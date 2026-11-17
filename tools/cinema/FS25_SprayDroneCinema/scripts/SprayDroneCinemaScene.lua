-- Scéna: přestavba soupravy (tahač + vlek), skládání vleku, plnění, zakládání vozidel, let dronu.
-- Příkazy pro video v2 jsou v SprayDroneCinemaV2.lua; tady jsou jejich rozšíření bagLift target=mill, canisterPour from=box, spawnMod fill (přehled tools/cinema/v2/prikazy_v2.md).

local C = SprayDroneCinema

-- tahač -> { index kloubu tahače, index vstupního kloubu vlevku Middle/Mini }; Max má vstupy otočené (jako prepare_testsave.py)
C.HITCH = {
    pickup = { 1, 1 }, jd3650 = { 3, 2 }, mt655 = { 3, 2 }, mf8570 = { 2, 3 }, rtv = { 1, 1 },
}

local function hitchFor(tractorKind, trailerKind)
    local h = C.HITCH[tractorKind] or C.HITCH.pickup
    local input = h[2]
    if trailerKind == "max" then
        input = ({ [2] = 2, [3] = 1 })[input] or 1
    end
    return h[1], input
end

local function kindOfTractor(v)
    local cfg = C.cfg(v)
    for kind, pattern in pairs(C.ALIASES) do
        if C.HITCH[kind] ~= nil and cfg:find(pattern, 1, true) ~= nil then
            return kind
        end
    end
    return "pickup"
end

local function kindOfTrailer(v)
    local cfg = C.cfg(v)
    for _, kind in ipairs({ "mini", "middle", "max" }) do
        if cfg:find(C.ALIASES[kind]:lower(), 1, true) ~= nil then
            return kind
        end
    end
end

-- Volný tahač daného druhu: bez zapřažení a bez nářadí (preferuje současný tahač soupravy).
local function findFreeTractor(kind, current)
    local pattern = C.ALIASES[kind]:lower()
    local best
    for v in C.eachVehicle() do
        if C.cfg(v):find(pattern, 1, true) ~= nil and (v.getAttacherVehicle == nil or v:getAttacherVehicle() == nil)
            and (v.getAttachedImplements == nil or #v:getAttachedImplements() == 0 or v == current) then
            if v == current then
                return v
            end
            -- volí se nejnovější vozidlo (zásoba souprav je v savu založená po dvorních strojích)
            if best == nil or (v.id or 0) > (best.id or 0) then
                best = v
            end
        end
    end
    return best
end

-- Zapřažení s vyrovnáním: dítě se dosadí tak, aby jeho vstupní kloub ležel na kloubu rodiče (stejné natočení yaw), pak attachImplement.
function C.attachAligned(parent, child, jointIdx, inputIdx, yaw)
    local joint = parent.spec_attacherJoints.attacherJoints[jointIdx]
    local input = child.spec_attachable.inputAttacherJoints[inputIdx]
    if joint == nil or input == nil then
        return false, string.format("chybí kloub %s/%s", tostring(jointIdx), tostring(inputIdx))
    end
    local jx, jy, jz = getWorldTranslation(joint.jointTransform)
    local ox, oy, oz = localToLocal(input.node, child.rootNode, 0, 0, 0)
    local s, c = math.sin(yaw), math.cos(yaw)
    C.teleport(child, jx - (ox * c + oz * s), jy - oy + 0.02, jz - (-ox * s + oz * c), yaw)
    parent:attachImplement(child, inputIdx, jointIdx)
    return child:getAttacherVehicle() == parent, "zapřaženo"
end

local function foldDirection(unfolded)
    return unfolded and -1 or 1
end

function C.fillSet(trailer)
    local station = C.getStation(trailer)
    if station == nil then
        return "není vlek"
    end
    local notes = {}
    pcall(function()
        local idx = station.fillUnitIndex
        local level = trailer:getFillUnitFillLevel(idx)
        local ft = level > 0 and trailer:getFillUnitFillType(idx) or FillType.LIQUIDFERTILIZER
        local missing = trailer:getFillUnitCapacity(idx) - level
        trailer:addFillUnitFillLevel(trailer:getOwnerFarmId(), idx, missing, ft, ToolType.UNDEFINED, nil)
        local d = station.dieselFillUnitIndex
        trailer:addFillUnitFillLevel(trailer:getOwnerFarmId(), d, trailer:getFillUnitCapacity(d) - trailer:getFillUnitFillLevel(d), FillType.DIESEL,
            ToolType.UNDEFINED, nil)
        table.insert(notes, string.format("nádrž %.0f l", trailer:getFillUnitFillLevel(idx)))
    end)
    pcall(function()
        for _, b in ipairs(station.batteries) do
            b.charge = station.batteryCapacity
        end
        for k = 1, station.numDrones or 1 do
            local d = station.drones ~= nil and station.drones[k] or station
            if d.droneBattery ~= nil then
                d.battery = d.batteryCapacity
            end
            if d.state == 0 and d.tankCapacity ~= nil then
                d.droneFillLevel = d.tankCapacity
                -- bez shodného druhu přípravku čerpadlo náplň při servisu zahodí a plní znovu (~23 s)
                local release = FS25_SprayDroneTrailer
                if release ~= nil and release.SprayDroneStation ~= nil then
                    local source = release.SprayDroneStation.getFillSource(trailer)
                    if source ~= nil and source.fillType ~= nil then
                        d.droneFillType = source.fillType
                    end
                end
            end
        end
        trailer:raiseDirtyFlags(station.dirtyFlag)
        table.insert(notes, "baterie nabité")
    end)
    return table.concat(notes, ", ")
end

-- placeSet: x, z, yaw (stupně; 0 = k +Z, 90 = k +X), trailer = mini|middle|max, tractor = pickup|jd3650|mt655|mf8570|rtv (jinak současný tahač),
-- unfolded = true/false (rozložit/složit, animace), fill = true (nádrž, nafta, baterie plné).
local function placeOnce(a)
    local kind = (a.trailer or "middle"):lower()
    local trailer = C.findVehicle(kind)
    if trailer == nil then
        return false, "vlek nenalezen: " .. kind
    end
    local x, z = C.num(a.x, nil), C.num(a.z, nil)
    if x == nil or z == nil then
        return false, "chybí x, z"
    end
    local yaw = math.rad(C.num(a.yaw, 0))
    local notes = {}
    local tractor = trailer:getAttacherVehicle()
    local wantKind = (a.tractor ~= nil and a.tractor ~= "") and a.tractor:lower() or nil
    if tractor == nil and wantKind == nil then
        wantKind = "pickup"
    end
    if wantKind ~= nil and (tractor == nil or kindOfTractor(tractor) ~= wantKind) then
        local want = findFreeTractor(wantKind, tractor)
        if want == nil then
            table.insert(notes, "volný tahač " .. wantKind .. " není, ponechán současný")
        else
            tractor = want
        end
    end
    if tractor == nil then
        return false, "vlek nemá tahač"
    end

    if C.stopDriving ~= nil then
        C.stopDriving(tractor)
    end

    -- připojené nářadí vleku (mlýnek) se odpojí a po přesunu zapřáhne znovu
    local carried = {}
    for _, impl in ipairs(trailer:getAttachedImplements()) do
        table.insert(carried, { object = impl.object, joint = impl.jointDescIndex, input = impl.object.spec_attachable.inputAttacherJointDescIndex })
    end
    for _, item in ipairs(carried) do
        trailer:detachImplementByObject(item.object)
    end
    local current = trailer:getAttacherVehicle()
    if current ~= nil then
        current:detachImplementByObject(trailer)
    end
    if tractor.getAttacherVehicle ~= nil and tractor:getAttacherVehicle() ~= nil then
        tractor:getAttacherVehicle():detachImplementByObject(tractor)
    end

    if not C.bool(a.keepPlayer, false) and C.playerNear ~= nil then
        C.playerNear(x + 10, z + 10)
    end
    C.teleport(tractor, x, C.terrainY(x, z) + 0.5, z, yaw)
    local tkind = kindOfTractor(tractor)
    local jointIdx, inputIdx = hitchFor(tkind, kind)
    local ok, msg = C.attachAligned(tractor, trailer, jointIdx, inputIdx, yaw)
    table.insert(notes, ok and ("zapřaženo " .. tkind .. "+" .. kind) or ("zapřažení selhalo: " .. tostring(msg)))
    if not C.wheelsOk(trailer) then
        tractor:detachImplementByObject(trailer)
        ok, msg = C.attachAligned(tractor, trailer, jointIdx, inputIdx, yaw)
        table.insert(notes, C.wheelsOk(trailer) and "kola vleku opravena" or "KOLA VLEKU BEZ FYZIKY")
    end
    for _, item in ipairs(carried) do
        local jointFromTrailer = item.joint or 1
        local okc, msgc = C.attachAligned(trailer, item.object, jointFromTrailer, item.input or 1, yaw)
        table.insert(notes, okc and "nářadí vráceno" or ("nářadí: " .. tostring(msgc)))
    end
    if a.unfolded ~= nil then
        -- unfolded=true při placeSet rozbije fyziku kol (vlek pak levituje nebo se boří, tahač se převrací): vždy se skládá, rozložit přes příkaz fold
        pcall(function() trailer:setFoldState(foldDirection(false), false) end)
        table.insert(notes, C.bool(a.unfolded, false) and "složeno (rozložit příkazem fold)" or "skládá se")
    end
    if C.bool(a.fill, false) then
        table.insert(notes, C.fillSet(trailer))
    end
    if a.drone ~= nil then
        local station = C.getStation(trailer)
        table.insert(notes, "dron v sadě je daný konfigurací vleku (nelze změnit za běhu)" .. (station ~= nil and "" or "!"))
    end
    return ok, table.concat(notes, "; ")
end

-- Kola vleku nebo tahače občas po přesunu nemají fyzický tvar (nedeterministicky); placeSet proto po 1,5 s zkontroluje a přesun až 6x zopakuje.
C.handlers.placeSet = function(a)
    local ok, msg = placeOnce(a)
    if not ok then
        return ok, msg
    end
    local kind = (a.trailer or "middle"):lower()
    local attempts, t0 = 1, g_time
    return "pending", function()
        if g_time - t0 < 1500 then
            return nil
        end
        local trailer = C.findVehicle(kind)
        local tractor = trailer ~= nil and trailer:getAttacherVehicle() or nil
        if trailer ~= nil and C.wheelsOk(trailer) and (tractor == nil or C.wheelsOk(tractor)) then
            return true, msg .. "; pokusů " .. attempts
        end
        if attempts >= 12 then
            return false, "KOLA BEZ FYZIKY po " .. attempts .. " pokusech; " .. msg
        end
        attempts = attempts + 1
        t0 = g_time
        local ok2, msg2 = placeOnce(a)
        msg = msg2 or msg
        if not ok2 then
            return false, msg
        end
        return nil
    end
end

-- fold: trailer = alias, state = fold | unfold; wait=true čeká na dokončení animace
local function foldHandler(a)
    local trailer = C.findVehicle(a.trailer or "middle")
    if trailer == nil then
        return false, "vlek nenalezen"
    end
    local unfold = (a.state or "unfold"):lower() == "unfold"
    trailer:setFoldState(foldDirection(unfold), false)
    if C.bool(a.wait, false) then
        local target = unfold and 0 or 1
        return "pending", function()
            if math.abs(trailer:getFoldAnimTime() - target) < 0.02 then
                return true, unfold and "rozloženo" or "složeno"
            end
        end
    end
    return true, unfold and "rozkládá se" or "skládá se"
end
C.handlers.fold = foldHandler
C.handlers.foldTrailer = function(a)
    a.state = "fold"
    return foldHandler(a)
end
C.handlers.unfoldTrailer = function(a)
    a.state = "unfold"
    return foldHandler(a)
end

C.handlers.fillSet = function(a)
    local trailer = C.findVehicle(a.trailer or "middle")
    if trailer == nil then
        return false, "vlek nenalezen"
    end
    return true, C.fillSet(trailer)
end

-- spawn: xml = cesta k vozidlu (např. data/vehicles/kubota/rtvx1140/rtvx1140.xml), x, z, yaw
C.handlers.spawn = function(a)
    local xml = a.xml
    if xml == nil then
        return false, "chybí xml"
    end
    local x, z = C.num(a.x, 0), C.num(a.z, 0)
    local data = VehicleLoadingData.new()
    data:setFilename(xml)
    data:setPosition(x, C.terrainY(x, z) + 0.5, z)
    data:setRotation(0, math.rad(C.num(a.yaw, 0)), 0)
    data:setPropertyState(VehiclePropertyState.OWNED)
    data:setOwnerFarmId(g_currentMission:getFarmId())
    data:load(function(_, vehicles, state)
        local v = vehicles ~= nil and vehicles[1] or nil
        C.log("spawn %s: %s id=%s", xml, tostring(state), v ~= nil and tostring(v.id) or "-")
    end)
    return true, "spawn odeslán"
end

---------------------------------------------------------------------------------------------------
-- dron

local function droneTrailer(a)
    return C.findVehicle(a.trailer or "middle")
end

local function droneSpec(trailer, k)
    local station = C.getStation(trailer)
    if station == nil then
        return nil
    end
    return station.drones ~= nil and station.drones[k] or (k == 1 and station or nil), station
end

C.handlers.selectField = function(a)
    local trailer = droneTrailer(a)
    if trailer == nil or trailer.sprayDroneCommand == nil then
        return false, "vlek nenalezen"
    end
    local id = C.num(a.field, nil)
    if C.bool(a.own, true) and id ~= nil then
        pcall(function() g_farmlandManager:setLandOwnership(id, trailer:getOwnerFarmId()) end)
    end
    trailer:sprayDroneCommand(1, id)
    local _, station = droneSpec(trailer, 1)
    return station.fieldId == id, "vybrané pole " .. tostring(station.fieldId)
end

-- resetField: smaže paměť dronu, kde už na vybraném poli postříkal (SprayDroneCommandEvent.RESET_FIELD = 5); bez toho další let jen dopostřikuje zbytek
C.handlers.resetField = function(a)
    local trailer = droneTrailer(a)
    if trailer == nil or trailer.sprayDroneCommand == nil then
        return false, "vlek nenalezen"
    end
    trailer:sprayDroneCommand(5, 0)
    return true, "paměť pokrytí smazána"
end

C.handlers.startFlight = function(a)
    local trailer = droneTrailer(a)
    if trailer == nil or trailer.sprayDroneCommand == nil then
        return false, "vlek nenalezen"
    end
    if C.bool(a.fill, true) then
        C.fillSet(trailer)
    end
    if a.field ~= nil then
        local ok, msg = C.handlers.selectField(a)
        if not ok then
            return false, msg
        end
    end
    local _, station = droneSpec(trailer, 1)
    if station.fieldId == 0 then
        return false, "není vybrané pole"
    end
    if not trailer:getIsUnfolded() then
        return false, "vlek není rozložený"
    end
    trailer:sprayDroneCommand(2, 0, nil, C.num(a.drone, 0))
    local d = droneSpec(trailer, 1)
    return true, string.format("start, pole %d, mission=%s state=%s", station.fieldId, tostring(d.missionActive), tostring(d.state))
end

C.handlers.returnHome = function(a)
    local trailer = droneTrailer(a)
    if trailer == nil or trailer.sprayDroneCommand == nil then
        return false, "vlek nenalezen"
    end
    trailer:sprayDroneCommand(3, 0, nil, C.num(a.drone, 0))
    return true, "návrat"
end

local function describeDrone(trailer, k)
    local d = droneSpec(trailer, k)
    if d == nil then
        return nil
    end
    local node = d.node
    local x, y, z = 0, 0, 0
    if node ~= nil then
        x, y, z = getWorldTranslation(node)
    end
    local spraying = d.lastSprayTime ~= nil and d.lastSprayTime + 150 > g_time
    return d, string.format("d%d state=%s air=%s mission=%s spray=%s pos=%.1f,%.1f,%.1f status=%s fill=%.1f bat=%.0f", k, tostring(d.state),
        tostring(d.airborne), tostring(d.missionActive), tostring(spraying), x, y, z, tostring(d.status), d.droneFillLevel or -1, d.battery or -1), spraying
end

C.handlers.droneStatus = function(a)
    local trailer = droneTrailer(a)
    if trailer == nil or C.getStation(trailer) == nil then
        return false, "vlek nenalezen"
    end
    local out = {}
    for k = 1, C.getStation(trailer).numDrones or 1 do
        local _, text = describeDrone(trailer, k)
        table.insert(out, text)
    end
    return true, table.concat(out, " | ")
end

-- waitDrone: cond = airborne | spraying | parked | flying, drone = 1|2
C.handlers.waitDrone = function(a)
    local trailer = droneTrailer(a)
    if trailer == nil or C.getStation(trailer) == nil then
        return false, "vlek nenalezen"
    end
    local k = C.num(a.drone, 1)
    local cond = (a.cond or "spraying"):lower()
    return "pending", function()
        local d, text, spraying = describeDrone(trailer, k)
        if d == nil then
            return false, "dron nenalezen"
        end
        local met = (cond == "airborne" and d.airborne) or (cond == "spraying" and spraying) or (cond == "parked" and d.state == 0)
            or (cond == "flying" and d.state == 1) or (cond == "returning" and d.state == 2) or (cond == "servicing" and d.state == 3)
        if cond == "near" and d.node ~= nil then
            local dx, _, dz = getWorldTranslation(d.node)
            local tx, _, tz = getWorldTranslation(trailer.rootNode)
            met = d.state == 2 and math.sqrt((dx - tx) ^ 2 + (dz - tz) ^ 2) < C.num(a.dist, 25)
        end
        if met then
            return true, cond .. ": " .. text
        end
    end
end

-- padDrone: dron na plošinu Maxu (pad = 1|2, variant = S|M|L, prázdné = odebrat); volá veřejnou funkci release módu přes jeho tabulku prostředí
C.handlers.padDrone = function(a)
    local trailer = C.findVehicle(a.trailer or "max")
    local release = FS25_SprayDroneTrailer
    if trailer == nil or release == nil or release.SprayDroneStation == nil then
        return false, "vlek nebo release mód nedostupný"
    end
    local problem = release.SprayDroneStation.setPadDrone(trailer, C.num(a.pad, 1), a.variant or "M")
    if problem ~= nil then
        return false, "odmítnuto: " .. tostring(problem)
    end
    return true, string.format("plošina %s: %s", tostring(a.pad or 1), tostring(a.variant or "M"))
end

-- nodeVis: trailer, show = "id1,id2", hide = "id3" (jména z i3dMappings vleku, např. antennaLarge, gpsRtkBox, antennaBase); jen vzhled, bez konfigurace vleku
C.handlers.nodeVis = function(a)
    local trailer = C.findVehicle(a.trailer or "middle")
    if trailer == nil or trailer.i3dMappings == nil then
        return false, "vlek nenalezen"
    end
    local notes = {}
    local function apply(list, visible)
        for id in tostring(list or ""):gmatch("[^,%s]+") do
            local m = trailer.i3dMappings[id]
            local node = m ~= nil and (m.nodeId or m) or nil
            if type(node) == "number" then
                setVisibility(node, visible)
                table.insert(notes, id .. (visible and "+" or "-"))
            else
                table.insert(notes, id .. "?")
            end
        end
    end
    apply(a.show, true)
    apply(a.hide, false)
    return true, table.concat(notes, " ")
end

-- Přesun samostatného (odpojeného) vozidla: kvůli fyzikálním kloubům mezi komponentami ven z fyziky a zpět.
function C.teleport(v, x, y, z, yaw)
    v:removeFromPhysics()
    v:setAbsolutePosition(x, y, z, 0, yaw, 0)
    v:addToPhysics()
end

-- Kola vleku musí mít fyzikální tvar (wheelShape ~= 0); savem založený vlek ho nemá a pak levituje nebo se boří do terénu.
function C.wheelsOk(v)
    local w = v.spec_wheels
    if w == nil then
        return true
    end
    for _, wh in ipairs(w.wheels) do
        if wh.physics ~= nil and wh.physics.wheelShape == 0 then
            return false
        end
    end
    return true
end

-- groundCheck: vehicles = "middle,pickup,..." (aliasy); kontrola, že každé kolo má fyzikální tvar a střed kola leží v rozumné výšce nad terénem
-- (poloměr -0,12 až +0,30 m, jinak vozidlo levituje, je zabořené nebo stojí na překážce) a že vozidlo není nakloněné přes ~6°.
C.handlers.groundCheck = function(a)
    local problems, report = {}, {}
    for kind in string.gmatch(a.vehicles or "pickup,middle", "[^,%s]+") do
        local v = C.findVehicle(kind)
        if v == nil then
            table.insert(problems, kind .. ": nenalezen")
        else
            local w = v.spec_wheels
            local lo, hi = 99, -99
            if w ~= nil then
                for _, wh in ipairs(w.wheels) do
                    if wh.physics ~= nil then
                        if wh.physics.wheelShape == 0 then
                            table.insert(problems, kind .. ": kolo bez fyziky")
                        end
                        local x, y, z = getWorldTranslation(wh.repr)
                        local d = y - getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z) - (wh.physics.radius or 0)
                        lo, hi = math.min(lo, d), math.max(hi, d)
                    end
                end
            end
            local _, uy, _ = localDirectionToWorld(v.rootNode, 0, 1, 0)
            local tilt = math.deg(math.acos(math.min(1, math.max(-1, uy))))
            table.insert(report, string.format("%s kola %.2f..%.2f sklon %.1f°", kind, lo, hi, tilt))
            if hi > -99 and (lo < -0.18 or hi > 0.30) then
                table.insert(problems, string.format("%s: kola %.2f..%.2f m od terénu", kind, lo, hi))
            end
            if tilt > C.num(a.maxTilt, 6) then
                table.insert(problems, string.format("%s: náklon %.1f°", kind, tilt))
            end
        end
    end
    if #problems > 0 then
        return false, table.concat(problems, "; ") .. " [" .. table.concat(report, "; ") .. "]"
    end
    return true, table.concat(report, "; ")
end

-- Hráč: fyzika kol a terénu se u vozidel daleko od hráče nenačte (vlek pak levituje nebo kola nemají tvar), proto se hráč před přesunem soupravy
-- přenese vedle cíle (kamera ho skrývá). playerTo: x, z; playerHome vrátí hráče na původní místo.
function C.playerNear(x, z)
    local p = g_localPlayer
    if p == nil or p.rootNode == nil then
        return false
    end
    if C.playerHomePos == nil then
        local px, py, pz = getWorldTranslation(p.rootNode)
        C.playerHomePos = { px, py, pz }
    end
    local cx, _, cz = getWorldTranslation(p.rootNode)
    if math.sqrt((cx - x) ^ 2 + (cz - z) ^ 2) < 30 then
        return true
    end
    local ok = pcall(function() p:teleportTo(x, C.terrainY(x, z) + 0.3, z, true, true) end)
    return ok
end

C.handlers.playerTo = function(a)
    local x, z = C.num(a.x, 0), C.num(a.z, 0)
    if C.bool(a.force, false) then
        if C.playerHomePos == nil and g_localPlayer ~= nil and g_localPlayer.rootNode ~= nil then
            local px, py, pz = getWorldTranslation(g_localPlayer.rootNode)
            C.playerHomePos = { px, py, pz }
        end
        local ok = pcall(function() g_localPlayer:teleportTo(x, C.terrainY(x, z) + 0.3, z, true, true) end)
        return ok, ok and "hráč přenesen (force)" or "teleport hráče selhal"
    end
    local ok = C.playerNear(x, z)
    return ok, ok and "hráč přenesen" or "teleport hráče selhal"
end

C.handlers.playerHome = function()
    local h = C.playerHomePos
    if h == nil then
        return true, "hráč nebyl přenesen"
    end
    local ok = pcall(function() g_localPlayer:teleportTo(h[1], h[2], h[3], true, true) end)
    C.playerHomePos = nil
    return ok, ok and "hráč zpět" or "teleport hráče selhal"
end

---------------------------------------------------------------------------------------------------
-- rekvizity: mlýnek, ladicí funkce release módu (SprayDroneDebug), couvání s tahačem na zapřažení

local function releaseDebug()
    local r = FS25_SprayDroneTrailer
    return r ~= nil and r.SprayDroneDebug or nil
end

-- play: trailer = max|middle, command = příkaz SprayDroneDebug.play (spawnHopper, hopperOn, hopperBigBag, fillLime, millModeBag, ...)
C.handlers.play = function(a)
    local d = releaseDebug()
    local t = C.findVehicle(a.trailer or "max")
    if d == nil or t == nil or a.command == nil then
        return false, "SprayDroneDebug nebo vlek nedostupný"
    end
    d.play(t, a.command)
    return true, "play " .. a.command
end

-- dbg: command = příkaz SprayDroneDebug.runGlobal (spawnPump, pumpOn, whConnect1, whPond, whOut, whValve, whDrop, whStatus, pumpModeTank, ...)
C.handlers.dbg = function(a)
    local d = releaseDebug()
    if d == nil or a.command == nil then
        return false, "SprayDroneDebug nedostupný"
    end
    d.runGlobal(a.command)
    return true, "dbg " .. a.command
end

-- dbgCmd: trailer, command = příkaz SprayDroneDebug.runCommand (fillWater, fillConcentrate, fillDiesel, chargeAll, toolboxFill, toolboxOpen, spawnCanister, tiltCanister,
-- holdCanister, dropOnBox, handPour, status, coverField, ...); globální příkazy mají dbg
C.handlers.dbgCmd = function(a)
    local d = releaseDebug()
    local t = C.findVehicle(a.trailer or "max")
    if d == nil or t == nil or a.command == nil then
        return false, "SprayDroneDebug nebo vlek nedostupný"
    end
    d.commandId = (d.commandId or 0) + 1
    d.runCommand(t, a.command)
    return true, "dbgCmd " .. a.command
end

-- millDbg: command = millOn | millOff | millFill
C.handlers.millDbg = function(a)
    local d = releaseDebug()
    if d == nil then
        return false, "SprayDroneDebug nedostupný"
    end
    d.mill(a.command or "millOn")
    return true, "mill " .. tostring(a.command)
end

-- Nastaví hladinu fill unit na přesně liters daného druhu; přes nulu nejde (vanilla big bag a palety se při vyprázdnění sami smažou), proto jen rozdíl,
-- vyprázdnění jen při jiném druhu. Vrací výslednou hladinu.
function C.setFillLevel(v, unit, fillType, liters)
    local farm = v:getOwnerFarmId()
    local level = v:getFillUnitFillLevel(unit)
    if level > 0.001 and v:getFillUnitFillType(unit) ~= fillType then
        v:addFillUnitFillLevel(farm, unit, -level, v:getFillUnitFillType(unit), ToolType.UNDEFINED, nil)
        level = v:getFillUnitFillLevel(unit)
    end
    if math.abs(liters - level) > 0.001 then
        v:addFillUnitFillLevel(farm, unit, liters - level, fillType, ToolType.UNDEFINED, nil)
    end
    return v:getFillUnitFillLevel(unit)
end

-- spawnMod: rel = cesta v modu (vehicles/sdtLimeMill/sdtLimeMill.xml), mod (výchozí release mód; base = rel je cesta v data hry), x, z, yaw (stupně), once = true: nic, když už vozidlo existuje (alias),
-- diesel / water = litry, fill = jméno druhu (SDT_FINE_LIME, LIME, ...) a liters (výchozí plná kapacita): naplní první fill unit, který druh přijímá (big bag, cisterna),
-- still = true: kinematické těleso (stojí na místě)
C.handlers.spawnMod = function(a)
    if a.once ~= nil and C.findVehicle(a.once) ~= nil then
        return true, "už existuje"
    end
    local mod = g_modManager:getModByName(a.mod or "FS25_SprayDroneTrailer")
    if a.rel == nil or (mod == nil and a.mod ~= "base") then
        return false, "mód nebo cesta chybí"
    end
    local x, z = C.num(a.x, 0), C.num(a.z, 0)
    if C.playerNear ~= nil then
        C.playerNear(x + 8, z + 8)
    end
    local data = VehicleLoadingData.new()
    data:setFilename(a.mod == "base" and a.rel or (mod.modDir .. a.rel))
    data:setPosition(x, C.terrainY(x, z) + C.num(a.lift, 0.5), z)
    data:setRotation(0, math.rad(C.num(a.yaw, 0)), 0)
    data:setPropertyState(VehiclePropertyState.OWNED)
    data:setOwnerFarmId(g_currentMission:getFarmId())
    data:load(function(_, vehicles, state)
        local v = vehicles ~= nil and vehicles[1] or nil
        C.log("spawnMod %s: %s id=%s", a.rel, tostring(state), v ~= nil and tostring(v.id) or "-")
        if v == nil then
            return
        end
        local farm = g_currentMission:getFarmId()
        if a.diesel ~= nil then
            local ps = v["spec_FS25_SprayDroneTrailer.sprayDronePump"]
            if ps ~= nil then
                v:addFillUnitFillLevel(farm, ps.dieselUnit, C.num(a.diesel, 10), FillType.DIESEL, ToolType.UNDEFINED, nil)
            end
        end
        if a.water ~= nil then
            for i = 1, #v.spec_fillUnit.fillUnits do
                if v:getFillUnitSupportsFillType(i, FillType.WATER) then
                    v:addFillUnitFillLevel(farm, i, C.num(a.water, 1000), FillType.WATER, ToolType.UNDEFINED, nil)
                    break
                end
            end
        end
        if a.fill ~= nil then
            local ft = g_fillTypeManager:getFillTypeIndexByName(a.fill:upper())
            local level = -1
            for i = 1, #v.spec_fillUnit.fillUnits do
                if ft ~= nil and v:getFillUnitSupportsFillType(i, ft) then
                    level = C.setFillLevel(v, i, ft, C.num(a.liters, v:getFillUnitCapacity(i)))
                    break
                end
            end
            C.log("spawnMod %s: fill %s -> %.1f l", a.rel, a.fill, level)
        end
        if C.bool(a.still, false) then
            setRigidBodyType(v.rootNode, RigidBodyType.KINEMATIC)
        end
    end)
    return true, "spawn odeslán"
end

-- lights: vehicle (alias), mask = lightsTypesMask (výchozí 3 = obrysová + potkávací; 0 vypne; 255 všechna)
C.handlers.lights = function(a)
    local v = C.findVehicle(a.vehicle or "jd3650")
    if v == nil or v.setLightsTypesMask == nil then
        return false, "vozidlo nemá světla"
    end
    v:setLightsTypesMask(C.num(a.mask, 3), true, true)
    return true, "světla " .. tostring(C.num(a.mask, 3))
end

-- generator: trailer, on = true/false (elektrocentrála, jako Alt+6); batteries = podíl nabití slotů (0..1; volitelně), fuel = litry nafty (volitelně)
C.handlers.generator = function(a)
    local trailer = C.findVehicle(a.trailer or "middle")
    local station = trailer ~= nil and C.getStation(trailer) or nil
    if station == nil then
        return false, "vlek nenalezen"
    end
    if a.batteries ~= nil then
        for _, b in ipairs(station.batteries) do
            b.charge = station.batteryCapacity * C.num(a.batteries, 1)
        end
        trailer:raiseDirtyFlags(station.dirtyFlag)
    end
    if a.fuel ~= nil and station.dieselFillUnitIndex ~= nil then
        local idx = station.dieselFillUnitIndex
        trailer:addFillUnitFillLevel(trailer:getOwnerFarmId(), idx, -1e6, FillType.DIESEL, ToolType.UNDEFINED, nil)
        trailer:addFillUnitFillLevel(trailer:getOwnerFarmId(), idx, C.num(a.fuel, 10), FillType.DIESEL, ToolType.UNDEFINED, nil)
    end
    if a.on ~= nil then
        trailer:sprayDroneCommand(4, C.bool(a.on, true) and 1 or 0)
    end
    return true, string.format("centrála=%s nabití %.0f", tostring(station.generatorEnabled), station.batteries[1] ~= nil and station.batteries[1].charge or -1)
end

-- droneSet: trailer, drone (1), battery = podíl kapacity (0..1), tank = litry v nádrži dronu; pro záběr servisu po přistání (nízká baterie, skoro prázdná nádrž)
C.handlers.droneSet = function(a)
    local trailer = C.findVehicle(a.trailer or "mini")
    local station = trailer ~= nil and C.getStation(trailer) or nil
    if station == nil then
        return false, "vlek nenalezen"
    end
    local k = C.num(a.drone, 1)
    local d = station.drones ~= nil and station.drones[k] or (k == 1 and station or nil)
    if d == nil then
        return false, "dron nenalezen"
    end
    if a.battery ~= nil and d.batteryCapacity ~= nil then
        d.battery = d.batteryCapacity * C.num(a.battery, 1)
    end
    if a.tank ~= nil then
        d.droneFillLevel = C.num(a.tank, 0)
    end
    trailer:raiseDirtyFlags(station.dirtyFlag)
    return true, string.format("baterie %.0f/%.0f nádrž %.1f", d.battery or -1, d.batteryCapacity or -1, d.droneFillLevel or -1)
end

-- setTank: trailer, unit = main | conc | diesel, fill = jméno druhu (WATER, LIQUIDFERTILIZER, SDT_FINE_LIME, SDT_CONCENTRATE_FERTILIZER, DIESEL) nebo EMPTY, liters (výchozí plná)
C.handlers.setTank = function(a)
    local trailer = C.findVehicle(a.trailer or "max")
    local station = trailer ~= nil and C.getStation(trailer) or nil
    local R = FS25_SprayDroneTrailer
    if station == nil or R == nil then
        return false, "vlek nenalezen"
    end
    local unit = (a.unit or "main"):lower()
    local idx
    if unit == "conc" then
        idx = R.SprayDroneStation.getConcentrateUnit(trailer)
    elseif unit == "diesel" then
        idx = station.dieselFillUnitIndex
    else
        idx = station.fillUnitIndex
    end
    if idx == nil then
        return false, "nádrž nenalezena"
    end
    local farm = trailer:getOwnerFarmId()
    trailer:addFillUnitFillLevel(farm, idx, -1e7, trailer:getFillUnitFillType(idx), ToolType.UNDEFINED, nil)
    local name = (a.fill or "EMPTY"):upper()
    if name ~= "EMPTY" then
        local ft = g_fillTypeManager:getFillTypeIndexByName(name)
        if ft == nil then
            return false, "druh neznámý: " .. name
        end
        local liters = C.num(a.liters, trailer:getFillUnitCapacity(idx))
        trailer:addFillUnitFillLevel(farm, idx, liters, ft, ToolType.UNDEFINED, nil)
    end
    return true, string.format("%s: %.0f l %s", unit, trailer:getFillUnitFillLevel(idx), tostring(g_fillTypeManager:getFillTypeNameByIndex(trailer:getFillUnitFillType(idx))))
end

-- stationAt: přenosnou pumpu (waterPump) postaví a.pd m (3) od a.port-tého vodního ventilu vleku (ven od jeho levého boku) a cisternu (waterTrailer550 / IBC) a.cd m (3.2) za ni;
-- a.dy posune pumpu i cisternu podél vleku (m, kladné = dopředu)
C.handlers.stationAt = function(a)
    local trailer = C.findVehicle(a.trailer or "max")
    local W = FS25_SprayDroneTrailer ~= nil and FS25_SprayDroneTrailer.SprayDroneWaterHose or nil
    if trailer == nil or W == nil then
        return false, "vlek nebo hadice nedostupné"
    end
    local water = {}
    for _, p in ipairs(W.getActivePorts(trailer)) do
        if p.port.kind == "water" then
            table.insert(water, p)
        end
    end
    local p = water[C.num(a.port, 1)]
    if p == nil then
        return false, "ventil nenalezen"
    end
    local x, _, z = getWorldTranslation(p.node)
    local ox, _, oz = localDirectionToWorld(trailer.rootNode, -1, 0, 0)
    local l = math.sqrt(ox * ox + oz * oz)
    ox, oz = ox / l, oz / l
    local fx, _, fz = localDirectionToWorld(trailer.rootNode, 0, 0, 1)
    local fl = math.sqrt(fx * fx + fz * fz)
    fx, fz = fx / fl, fz / fl
    local dy = C.num(a.dy, 0)
    local pd, cd = C.num(a.pd, 3), C.num(a.cd, 3.2)
    local px, pz = x + ox * pd + fx * dy, z + oz * pd + fz * dy
    local notes = {}
    local pump = C.findVehicle("waterPump")
    if pump ~= nil then
        pump:setAbsolutePosition(px, C.terrainY(px, pz) + 0.2, pz, 0, MathUtil.getYRotationFromDirection(-oz, ox), 0)
        table.insert(notes, "pumpa")
    end
    local cistern = C.findVehicle(a.cistern or "waterTrailer550")
    if cistern ~= nil then
        local cx, cz = px + ox * cd, pz + oz * cd
        C.teleport(cistern, cx, C.terrainY(cx, cz) + 0.3, cz, MathUtil.getYRotationFromDirection(fx, fz) + math.rad(C.num(a.cyaw, 0)))
        table.insert(notes, "cisterna")
    end
    return true, table.concat(notes, "+") .. string.format(" u %.1f,%.1f", px, pz)
end

-- removeVehicle: alias (první nález); all = true smaže všechny nálezy
C.handlers.removeVehicle = function(a)
    local n = 0
    local alias = a.vehicle or "mill"
    local pattern = (C.ALIASES[alias:lower()] or alias):lower()
    local list = {}
    for v in C.eachVehicle() do
        if not v.isDeleted and C.cfg(v):find(pattern, 1, true) ~= nil then
            table.insert(list, v)
        end
    end
    for _, v in ipairs(list) do
        if v.getAttacherVehicle ~= nil and v:getAttacherVehicle() ~= nil then
            v:getAttacherVehicle():detachImplementByObject(v)
        end
        v:delete()
        n = n + 1
        if not C.bool(a.all, false) then
            break
        end
    end
    return true, "smazáno " .. n
end

-- moveVehicle: odpojené vozidlo na x, z, yaw (stupně)
C.handlers.moveVehicle = function(a)
    local v = C.findVehicle(a.vehicle or "mill")
    if a.id ~= nil then
        v = nil
        for w in C.eachVehicle() do
            if tostring(w.id) == tostring(a.id) then
                v = w
            end
        end
    end
    if v == nil then
        return false, "vozidlo nenalezeno"
    end
    local x, z = C.num(a.x, 0), C.num(a.z, 0)
    if C.playerNear ~= nil then
        C.playerNear(x + 8, z + 8)
    end
    C.teleport(v, x, C.terrainY(x, z) + C.num(a.lift, 0.3), z, math.rad(C.num(a.yaw, 0)))
    return true, "přesunuto"
end

-- attachTo: parent (výchozí max) zapřáhne child (výchozí mill) za zadní kloub, bez couvání (přímé zapřažení na místě)
local function findInputFor(parent, child, jointIdx)
    local joint = parent.spec_attacherJoints.attacherJoints[jointIdx]
    for i, input in ipairs(child.spec_attachable.inputAttacherJoints) do
        if input.jointType == joint.jointType then
            return i
        end
    end
    return 1
end

C.handlers.attachTo = function(a)
    local parent, child = C.findVehicle(a.parent or "max"), C.findVehicle(a.child or "mill")
    if parent == nil or child == nil then
        return false, "vozidlo nenalezeno"
    end
    local ji = C.num(a.joint, 1)
    local ii = findInputFor(parent, child, ji)
    if a.yaw ~= nil then
        local ok, msg = C.attachAligned(parent, child, ji, ii, math.rad(C.num(a.yaw, 0)))
        return ok, msg
    end
    parent:attachImplement(child, ii, ji)
    return child:getAttacherVehicle() == parent, "zapřaženo"
end

C.handlers.detachFrom = function(a)
    local parent, child = C.findVehicle(a.parent or "max"), C.findVehicle(a.child or "mill")
    if parent == nil or child == nil then
        return false, "vozidlo nenalezeno"
    end
    parent:detachImplementByObject(child)
    return true, "odpojeno"
end

-- reverseAttach: tractor couvá s parent (vlek), dokud jeho zadní kloub není u vstupního kloubu child; pak zapřáhne. Couvá rovně (rotatedTime 0),
-- proto musí být child přesně za vlekem. kmh = nejvyšší rychlost, joint = index zadního kloubu vleku (1)
C.handlers.reverseAttach = function(a)
    local tractor, parent, child = C.findVehicle(a.vehicle or "mt655"), C.findVehicle(a.parent or "max"), C.findVehicle(a.child or "mill")
    if tractor == nil or parent == nil or child == nil then
        return false, "vozidlo nenalezeno"
    end
    C.stopDriving(tractor)
    if tractor:getIsInUse(nil) then
        return false, "vozidlo je používané"
    end
    local ji = C.num(a.joint, 1)
    C.rev = { tractor = tractor, parent = parent, child = child, ji = ji, ii = findInputFor(parent, child, ji), kmh = C.num(a.kmh, 4), stop = C.num(a.stop, 0.12),
        started = g_time, steer = C.num(a.steer, 0) }
    if not tractor:getIsMotorStarted() then
        tractor:startMotor()
    end
    pcall(function() tractor:setCruiseControlMaxSpeed(C.rev.kmh, C.rev.kmh) end)
    if C.bool(a.wait, true) then
        return "pending", function()
            if C.rev == nil or C.rev.done then
                local r = C.rev
                C.rev = nil
                return r ~= nil and r.attached == true, r ~= nil and r.msg or "bez couvání"
            end
        end
    end
    return true, "couvá"
end

function C.reverseFrame(dt)
    if C.bagFrame ~= nil then
        C.bagFrame(dt)
    end
    if C.poseFrame ~= nil then
        C.poseFrame(dt)
    end
    local r = C.rev
    if r == nil or r.done then
        return
    end
    if r.tractor.isDeleted or r.child.isDeleted then
        r.done, r.msg = true, "vozidlo zmizelo"
        return
    end
    local joint = r.parent.spec_attacherJoints.attacherJoints[r.ji]
    local input = r.child.spec_attachable.inputAttacherJoints[r.ii]
    local jx, _, jz = getWorldTranslation(joint.jointTransform)
    local ix, _, iz = getWorldTranslation(input.node)
    local dist = math.sqrt((ix - jx) ^ 2 + (iz - jz) ^ 2)
    if dist < r.stop or g_time - r.started > 60000 then
        pcall(function() AIVehicleUtil.driveToPoint(r.tractor, dt, 0, false, false, 0, -10, 1, true) end)
        r.parent:attachImplement(r.child, r.ii, r.ji)
        r.attached = r.child:getAttacherVehicle() == r.parent
        pcall(function() r.tractor:stopMotor() end)
        r.done, r.msg = true, string.format("zapřaženo=%s dist=%.2f po %.1f s", tostring(r.attached), dist, (g_time - r.started) * 0.001)
        return
    end
    local kmh = C.clamp(1.3 + dist * 0.9, 1.3, r.kmh)
    r.tractor.rotatedTime = r.steer
    AIVehicleUtil.driveToPoint(r.tractor, dt, 1, true, false, 0, -10, kmh, true)
end

---------------------------------------------------------------------------------------------------
-- big bag zvednutý nad násypku (kinematicky vedený místo nakladače)

local HOPPER_SPEC = "spec_FS25_SprayDroneTrailer.sprayDroneHopper"

local function findHopper()
    for v in C.eachVehicle() do
        if v[HOPPER_SPEC] ~= nil and not v.isDeleted then
            return v
        end
    end
end

local function lerp(a, b, u) return a + (b - a) * u end

-- bagLift (target = hopper | mill): big bag s a.fill l (300) jemného vápna (u mlýnku hrubého LIME ve vanilla big bagu) se vedle násypky (a.side m, směr a.dx a.dz) zvedne do a.up m, přenese nad ústí, spustí a vyklopí;
-- a.tLift, a.tMove, a.tLower (s), a.tHold = nejdéle tak dlouho drží nad ústím; po vyprázdnění ho za 1,5 s smaže (a.keep = true ho nechá ležet)
-- target = mill: big bag s hrubým vápnem (vanilla bigBag_lime, druh LIME) nad exactFillRootNode prvního fill unit mlýnku (a.fill l, výchozí 300) místo násypky
local function findMill()
    for v in C.eachVehicle() do
        if not v.isDeleted and C.cfg(v):find("sdtlimemill", 1, true) ~= nil then
            return v
        end
    end
end

local function millMouth(mill)
    local unit = mill.spec_fillUnit.fillUnits[1]
    local node = unit ~= nil and unit.exactFillRootNode or nil
    if type(node) == "table" then
        node = node.node
    end
    if node == nil and mill.i3dMappings ~= nil and mill.i3dMappings.exactFillRootNode ~= nil then
        local m = mill.i3dMappings.exactFillRootNode
        node = m.nodeId or m
    end
    return node
end

C.handlers.bagLift = function(a)
    local toMill = (a.target or "hopper"):lower() == "mill"
    local hopper = toMill and findMill() or findHopper()
    if hopper == nil then
        return false, toMill and "mlýnek nenalezen" or "násypka nenalezena"
    end
    local mod = g_modManager:getModByName("FS25_SprayDroneTrailer")
    local mouth = toMill and millMouth(hopper) or hopper[HOPPER_SPEC].pour.pourNeck
    if mouth == nil then
        return false, "ústí nenalezeno"
    end
    local nx, ny, nz = getWorldTranslation(mouth)
    if toMill then
        -- exactFillRootNode mlýnku je kolizní kvádr, jehož počátek leží u země; ústí je ve středu jeho obálky, big bag se drží o a.mouth m nad ním
        local cx, cy, cz = getShapeBoundingSphere(mouth)
        nx, ny, nz = localToWorld(mouth, cx, cy, cz)
        ny = ny + C.num(a.mouth, 0.8)
    end
    local side, up = C.num(a.side, 3.2), C.num(a.up, 3.4)
    local dx, dz = C.num(a.dx, 1), C.num(a.dz, 0)
    local l = math.sqrt(dx * dx + dz * dz)
    dx, dz = dx / l, dz / l
    local sx, sz = nx + dx * side, nz + dz * side
    local data = VehicleLoadingData.new()
    data:setFilename(toMill and "data/objects/bigBag/lime/bigBag_lime.xml" or (mod.modDir .. "objects/limeBigBag/limeBigBag.xml"))
    data:setPosition(sx, C.terrainY(sx, sz) + 0.1, sz)
    data:setRotation(0, math.rad(C.num(a.yaw, 0)), 0)
    data:setPropertyState(VehiclePropertyState.OWNED)
    data:setOwnerFarmId(g_currentMission:getFarmId())
    data:load(function(_, vehicles, state)
        local bag = vehicles ~= nil and vehicles[1] or nil
        if bag == nil then
            C.log("bagLift: big bag se nenačetl (%s)", tostring(state))
            return
        end
        local ft = toMill and FillType.LIME or g_fillTypeManager:getFillTypeIndexByName("SDT_FINE_LIME")
        C.setFillLevel(bag, 1, ft, C.num(a.fill, 300))
        setRigidBodyType(bag.rootNode, RigidBodyType.KINEMATIC)
        table.insert(C.bagJobs, {
            bag = bag, t = 0, start = { sx, C.terrainY(sx, sz) + 0.1, sz }, up = up, fin = { nx, ny + 0.5, nz }, side = { sx, sz },
            tLift = C.num(a.tLift, 3), tMove = C.num(a.tMove, 3), tLower = C.num(a.tLower, 1.5), tHold = C.num(a.tHold, 14), keep = C.bool(a.keep, false),
            delay = C.num(a.delay, 0),
        })
        C.log("bagLift: big bag id %s, %.0f l", tostring(bag.id), bag:getFillUnitFillLevel(1))
    end)
    return true, "big bag spawn"
end

C.bagJobs = C.bagJobs or {}

function C.bagFrame(dt)
    local jobs = C.bagJobs
    for i = #jobs, 1, -1 do
        local j = jobs[i]
        local bag = j.bag
        if bag.isDeleted then
            table.remove(jobs, i)
        else
            j.t = j.t + dt * 0.001
            local t = j.t - j.delay
            local x, y, z
            local s, f = j.start, j.fin
            local topY = math.max(s[2], f[2]) + j.up
            if t < 0 then
                x, y, z = s[1], s[2], s[3]
            elseif t < j.tLift then
                local u = C.ease("smooth", t / j.tLift)
                x, y, z = s[1], lerp(s[2], topY, u), s[3]
            elseif t < j.tLift + j.tMove then
                local u = C.ease("smooth", (t - j.tLift) / j.tMove)
                x, y, z = lerp(s[1], f[1], u), topY, lerp(s[3], f[3], u)
            elseif t < j.tLift + j.tMove + j.tLower then
                local u = C.ease("smooth", (t - j.tLift - j.tMove) / j.tLower)
                x, y, z = f[1], lerp(topY, f[2], u), f[3]
            else
                x, y, z = f[1], f[2], f[3]
                local empty = bag:getFillUnitFillLevel(1) < 1
                if empty and j.emptyAt == nil then
                    j.emptyAt = t
                end
                if (j.emptyAt ~= nil and t - j.emptyAt > 1.5) or t > j.tLift + j.tMove + j.tLower + j.tHold then
                    if j.keep then
                        setRigidBodyType(bag.rootNode, RigidBodyType.DYNAMIC)
                    else
                        bag:delete()
                    end
                    table.remove(jobs, i)
                    x = nil
                end
            end
            if x ~= nil then
                bag.sdtEjectTime = g_time
                bag:setAbsolutePosition(x, y, z, 0, 0, 0)
            end
        end
    end
end

C.handlers.bagStatus = function()
    local out = {}
    for v in C.eachVehicle() do
        if C.cfg(v):find("limebigbag", 1, true) ~= nil or C.cfg(v):find("bigbag_lime", 1, true) ~= nil then
            local x, y, z = getWorldTranslation(v.rootNode)
            table.insert(out, string.format("bag id=%s %.1f l pos %.1f %.1f %.1f", tostring(v.id), v:getFillUnitFillLevel(1), x, y, z))
        end
    end
    local h = findHopper()
    if h ~= nil then
        local s = h[HOPPER_SPEC]
        table.insert(out, string.format("hopper lime %.1f l", h:getFillUnitFillLevel(s.limeUnit)))
    end
    local mill = findMill()
    if mill ~= nil then
        table.insert(out, string.format("mlýnek hrubé %.1f l, jemné %.1f l", mill:getFillUnitFillLevel(1), mill:getFillUnitFillLevel(3)))
    end
    return true, table.concat(out, " | ") .. " jobs=" .. #C.bagJobs
end

---------------------------------------------------------------------------------------------------
-- kanystr nalévaný do koncentrátové nádrže (kinematicky vedený místo rukou)

C.poseJobs = C.poseJobs or {}

-- canisterPour: trailer, fill = fertilizer | herbicide | diesel, liters (20), side (1.1 m od hrdla ven), tLift 2, tTilt 2, tPour 7, delay (s před zvednutím), keep;
-- from = box, slot = n: kanystr se vezme z police bedny (slot toolboxCanister<n>; bez slot první obsazený, bez fill druh i litry podle slotu), vizuál slotu je po dobu pohybu skrytý
-- a kanystr se po vylití smaže, takže slot zůstane obsazený (poloha slotu: začátek i konec dráhy)
C.handlers.canisterPour = function(a)
    local trailer = C.findVehicle(a.trailer or "max")
    local station = trailer ~= nil and C.getStation(trailer) or nil
    local R = FS25_SprayDroneTrailer
    if station == nil or R == nil then
        return false, "vlek nenalezen"
    end
    local tb = station.toolbox
    local kinds = { fertilizer = FillType.SDT_CONCENTRATE_FERTILIZER, herbicide = FillType.SDT_CONCENTRATE_HERBICIDE, diesel = FillType.DIESEL }
    local fillType = a.fill ~= nil and kinds[a.fill:lower()] or nil
    local liters = C.num(a.liters, 20)
    local slot
    if (a.from or ""):lower() == "box" then
        slot = C.num(a.slot, nil)
        if slot == nil then
            for i = 1, tb.slots do
                local c = tb.canisters[i]
                if c.fillType ~= FillType.UNKNOWN and c.liters > 0.001 and (fillType == nil or c.fillType == fillType) then
                    slot = i
                    break
                end
            end
        end
        local c = slot ~= nil and tb.canisters[slot] or nil
        if c == nil or c.fillType == FillType.UNKNOWN or tb.canisterNodes[slot] == nil then
            return false, "slot " .. tostring(slot) .. " je prázdný nebo bez uzlu"
        end
        if fillType == nil then
            fillType, liters = c.fillType, a.liters ~= nil and liters or c.liters
        end
    end
    fillType = fillType or kinds.fertilizer
    local diesel = fillType == FillType.DIESEL
    local neck = diesel and tb.dieselNeckNode or tb.neckNode
    if neck == nil then
        return false, "hrdlo nenalezeno"
    end
    local nx, ny, nz = getWorldTranslation(neck)
    local ox, _, oz = localDirectionToWorld(trailer.rootNode, diesel and 1 or -1, 0, 0)
    local l = math.sqrt(ox * ox + oz * oz)
    ox, oz = ox / l, oz / l
    local side = C.num(a.side, 1.1)
    local sx, sz = nx + ox * side, nz + oz * side
    local sy = C.terrainY(sx, sz) + 0.15
    local bx, by, bz = sx, sy, sz
    if slot ~= nil then
        bx, by, bz = getWorldTranslation(tb.canisterNodes[slot])
    end
    local lift, tilt, pour = C.num(a.tLift, 2), C.num(a.tTilt, 2), C.num(a.tPour, 7)
    local ok, reason = R.SprayDroneToolbox.spawnCanister(trailer, fillType, liters, function(success, vehicle)
        if not success then
            C.log("canisterPour: kanystr se nevyrobil")
            return
        end
        setRigidBodyType(vehicle.rootNode, RigidBodyType.KINEMATIC)
        local topY = ny + 0.45
        local job = {
            v = vehicle, t = -C.num(a.delay, 0), keep = C.bool(a.keep, false),
            keys = {
                { 0, bx, by, bz, 0 },
                { lift, sx, topY, sz, 0 },
                { lift + tilt, nx + 0.062, ny + 0.367, nz, math.pi },
                { lift + tilt + pour, nx + 0.062, ny + 0.367, nz, math.pi },
                { lift + tilt + pour + 1.5, sx, topY, sz, 0 },
                { lift + tilt + pour + 3.0, bx, by, bz, 0 },
            },
        }
        if slot ~= nil then
            local node = tb.canisterNodes[slot]
            setVisibility(node, false)
            job.onDone = function()
                tb.canisterShown[slot] = nil
            end
        end
        table.insert(C.poseJobs, job)
        C.log("canisterPour: kanystr id %s%s", tostring(vehicle.id), slot ~= nil and (" ze slotu " .. slot) or "")
    end, { bx, by, bz, 0 })
    return ok ~= false, "kanystr spawn " .. tostring(reason or slot or "")
end

function C.poseFrame(dt)
    local jobs = C.poseJobs
    for i = #jobs, 1, -1 do
        local j = jobs[i]
        if j.v.isDeleted then
            if j.onDone ~= nil then
                j.onDone()
            end
            table.remove(jobs, i)
        else
            j.t = j.t + dt * 0.001
            local keys = j.keys
            local t = math.max(j.t, 0)
            local last = keys[#keys]
            if t >= last[1] then
                if j.keep then
                    setRigidBodyType(j.v.rootNode, RigidBodyType.DYNAMIC)
                else
                    j.v:delete()
                end
                if j.onDone ~= nil then
                    j.onDone()
                end
                table.remove(jobs, i)
            else
                local k = 1
                while keys[k + 1][1] <= t do
                    k = k + 1
                end
                local p, q = keys[k], keys[k + 1]
                local u = C.ease("smooth", (t - p[1]) / math.max(q[1] - p[1], 0.001))
                j.v.sdtEjectTime = g_time
                j.v:setAbsolutePosition(lerp(p[2], q[2], u), lerp(p[3], q[3], u), lerp(p[4], q[4], u), 0, 0, lerp(p[5], q[5], u))
            end
        end
    end
end
