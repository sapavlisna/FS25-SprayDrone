-- Skládací bedna s dronem u malého vleku (docs/DRON.md, „Malý vlek“). Ve složeném stavu je bedna vzpřímená a celou
-- základnou leží na palubě (tři ploché panely P/H/Z svislé i vodorovné, dron stojí přímo na palubě uvnitř, otočený o
-- 90° navíc, aby se vešel na šířku vleku; po stranách stojí plechové boční stěny padSideL/R s polepem). Panely jsou zavěšené řetězem čepů
-- padHingeZ -> padHingeH -> padHingeP (stejná osa X u všech tří, úhly v hierarchii se sčítají): v i3d mají úhel 90° (bedna),
-- při rozložení skript sveze úhel všech tří k 0° a panely se srovnají do jedné roviny - samostatné plošiny, která už se nemusí
-- dotýkat vleku. Na plošině jsou nožičky padLeg1..6 (po dvou na padHingeH/padHingeP/padHingeEnd, kam je rozložení donese; ve
-- složené bedně skryté), které se vysunou a plošinu vyrovnají vodorovně o terén (vlek může stát šikmo). Dron stojí celou dobu
-- skládání na palubě (panely se vyklápí nahoru a dozadu, dronem neprocházejí) a teprve po rozložení a vyrovnání plošiny se
-- nadzvedne, otočí o droneYaw zpět do letové osy a přejede na střed plošiny. Pohyb jde z času skládání vleku (0 = rozloženo,
-- 1 = složeno), nic se neanimuje v XML:
--
--   t >= foldStart            bedna stojí složená na palubě, dron uvnitř, boční stěny stojí svisle na hraně paluby
--   foldStart .. foldEnd      D 0..1: boční stěny se kolem spodní hrany na lemu paluby vyklopí ven a sklopí k zemi (0 - 0,14; úhel se dorovná
--                             podle terénu pod nimi, pochozí vnitřní strana je pak nahoře), panely se rozklopí
--                             do roviny (0,14 - 0,38; všechny tři čepy o stejný úhel, takže stěna P jede od dronu pryč a střecha H nad
--                             ním; v posledních 20 % se plynule objeví nožičky), nožičky se vysunou a plošina se vyrovná (0,38 - 0,53),
--                             dron se nadzvedne (0,53 - 0,61), otočí a přejede na střed plošiny (0,61 - 0,92) a dosedne (0,92 - 1)
--   t <= foldEnd              plošina stojí na nožičkách, dron se rozkládá (sprayDrone#trailerFoldEnd)
--
-- Skládání je opačně (boční stěny se na konci zvednou zpět na lem paluby pod střechu). Před rozložením se zkontroluje, že na místě
-- plošiny nic nestojí, že terén není moc svažitý ani vysoký a že hadice k dronu dosáhne. Jen malý vlek: bez uzlu padAnchor se vše
-- přeskočí.

SprayDronePad = {}

SprayDronePad.LEG_COUNT = 6
SprayDronePad.SIDE_END = 0.14           -- konec vyklápění bočních stěn (D); pak se skládají panely
SprayDronePad.FOLD_END = 0.38           -- konec rozkládání panelů
SprayDronePad.LEGS_END = 0.53           -- konec vysouvání nožiček
SprayDronePad.LIFT_END = 0.61           -- dron je nadzvednutý
SprayDronePad.MOVE_END = 0.92           -- dron je na středu plošiny
SprayDronePad.LEG_SHOW = 0.8            -- od tohoto podílu rozložení panelů se nožičky plynule zvětšují z nuly
SprayDronePad.SIDE_FALL_MIN = math.rad(100)  -- nejmenší a největší vyklopení boční stěny od svislice (90° = vodorovně)
SprayDronePad.SIDE_FALL_MAX = math.rad(165)
SprayDronePad.SIDE_REACH = 0.5          -- podíl délky stěny, kterým sahá bokem od čepu, kde se měří terén
SprayDronePad.SIDE_CLEARANCE = 0.012    -- o kolik zůstane spodní hrana sklopené stěny nad terénem (m)
SprayDronePad.MARGIN = 0.10             -- rezerva kolem plošiny při hledání překážek (m)
SprayDronePad.PLATE_CLEARANCE = 0.04    -- nejmenší odstup spodku plošiny nad terénem pod ní
SprayDronePad.CORRIDOR_HEIGHT = 0.8     -- volno nad složenou bednou (m, navíc k liftHeight): sem se při rozkládání vyklápí panely
SprayDronePad.HOSE_SLACK = 1.10         -- prověšení hadice: tolikrát je delší než vzdálenost konců
SprayDronePad.HOSE_ARC = 0.12           -- přídavek na oblouk k hrdlu (m)
SprayDronePad.STOWED_TIME = 0.999       -- od tohoto času skládání je bedna složená
SprayDronePad.SETTLE_FRAMES = 5
SprayDronePad.PREVIEW_CHECK_MS = 250    -- jak často obrys plošiny znovu hledá překážky (ms)

SprayDronePad.OVERLAP_MASK = CollisionFlag.STATIC_OBJECT + CollisionFlag.TREE + CollisionFlag.BUILDING
    + CollisionFlag.VEHICLE + CollisionFlag.DYNAMIC_OBJECT + CollisionFlag.PLAYER

local function smooth(t)
    t = math.clamp(t, 0, 1)
    return t * t * (3 - 2 * t)
end

-- Součet lokálních translací od node až po (nezahrnuje) root. Translace čepu/nožičky vůči rodiči se za běhu nikdy
-- nemění (skript otáčí jen rotaci), takže součet dá přesně polohu v "rozložené" (ploché, úhel všech čepů 0) referenci
-- bez ohledu na aktuální stav animace.
local function localOffsetTo(node, root)
    local ox, oy, oz = 0, 0, 0
    local n = node
    while n ~= nil and n ~= 0 and n ~= root do
        local tx, ty, tz = getTranslation(n)
        ox, oy, oz = ox + tx, oy + ty, oz + tz
        n = getParent(n)
    end
    return ox, oy, oz
end

function SprayDronePad.registerXMLPaths(schema, key)
    key = key .. ".pad"
    schema:register(XMLValueType.FLOAT, key .. "#foldStart", "Od jakého času skládání (0..1) je bedna složená", 0.825)
    schema:register(XMLValueType.FLOAT, key .. "#foldEnd", "Do jakého času skládání plošina stojí na nožičkách", 0.325)
    schema:register(XMLValueType.FLOAT, key .. "#legRest", "Délka tyče nožičky v modelu (m)", 0.02)
    schema:register(XMLValueType.FLOAT, key .. "#legFoot", "Tloušťka patky pod koncem tyče (m)", 0.025)
    schema:register(XMLValueType.FLOAT, key .. "#maxLegLength", "Nejdelší vysunutí nožičky (m)", 1.0)
    schema:register(XMLValueType.FLOAT, key .. "#maxHeightDiff", "Největší výškový rozdíl terénu pod nožičkami (m)", 0.5)
    schema:register(XMLValueType.FLOAT, key .. "#checkHeight", "Výška prostoru nad rozloženou plošinou, který musí být volný (m)", 1.2)
    schema:register(XMLValueType.FLOAT, key .. "#liftHeight", "O kolik se dron nadzvedne nad plošinu při otáčení a přejezdu na její střed (m)", 0.12)
    schema:register(XMLValueType.FLOAT, key .. "#droneYaw",
        "O kolik stupňů (i3d osa Y) je dron ve složené bedně otočený navíc oproti letové ose; při rozložení se carrier otočí o -droneYaw", 0)
    schema:register(XMLValueType.FLOAT, key .. "#droneSettle", "O kolik níž stojí na rozložené plošině než ve složené bedně (m)", 0)
    schema:register(XMLValueType.FLOAT, key .. "#sideLength", "Výška boční stěny od čepu ke vnější hraně (m); podle ní se dorovnává sklopení k zemi", 0.82)
end

function SprayDronePad.load(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.pad = nil
    local xml = self.xmlFile
    local key = "vehicle.sprayDrone.pad"
    local getMappedNode = SprayDroneStation.getMappedNode
    local anchor = getMappedNode(self, "padAnchor")
    local hingeZ, hingeH, hingeP = getMappedNode(self, "padHingeZ"), getMappedNode(self, "padHingeH"), getMappedNode(self, "padHingeP")
    local hingeEnd, carrier = getMappedNode(self, "padHingeEnd"), getMappedNode(self, "droneCarrier")
    if anchor == nil or hingeZ == nil or hingeH == nil or hingeP == nil or hingeEnd == nil or carrier == nil
        or not xml:hasProperty(key) then
        return
    end
    local pad = {
        anchor = anchor,
        hingeZ = hingeZ,
        hingeH = hingeH,
        hingeP = hingeP,
        sides = {},
        carrier = carrier,
        parent = getParent(anchor),
        legs = {},
        foldStart = xml:getValue(key .. "#foldStart", 0.825),
        foldEnd = xml:getValue(key .. "#foldEnd", 0.325),
        legRest = xml:getValue(key .. "#legRest", 0.02),
        legFoot = xml:getValue(key .. "#legFoot", 0.025),
        maxLegLength = xml:getValue(key .. "#maxLegLength", 1.0),
        maxHeightDiff = xml:getValue(key .. "#maxHeightDiff", 0.5),
        checkHeight = xml:getValue(key .. "#checkHeight", 1.2),
        liftHeight = xml:getValue(key .. "#liftHeight", 0.12),
        droneYaw = math.rad(xml:getValue(key .. "#droneYaw", 0)),
        droneSettle = xml:getValue(key .. "#droneSettle", 0),
        sideLength = xml:getValue(key .. "#sideLength", 0.82),
        stowPos = { getTranslation(anchor) },
        stowQuat = { getQuaternion(anchor) },
        carrierPos = { getTranslation(carrier) },
        carrierQuat = { getQuaternion(carrier) },
        settle = SprayDronePad.SETTLE_FRAMES,
    }
    for _, suffix in ipairs({ "L", "R" }) do
        local node = getMappedNode(self, "padSide" .. suffix)
        if node ~= nil then
            table.insert(pad.sides, { node = node, side = suffix == "L" and 1 or -1 })
        end
    end
    -- rozložená hloubka plošiny (anchor -> konec posledního panelu) v rovné referenci, pro plán a kontrolu překážek
    pad.endOffset = { localOffsetTo(hingeEnd, anchor) }
    pad.depth = MathUtil.vector3Length(pad.endOffset[1], 0, pad.endOffset[3])
    for i = 1, SprayDronePad.LEG_COUNT do
        local leg = getMappedNode(self, "padLeg" .. i)
        local rod = getMappedNode(self, "padLegRod" .. i)
        local foot = getMappedNode(self, "padLegFoot" .. i)
        if leg ~= nil and rod ~= nil and foot ~= nil then
            local x, _, z = localOffsetTo(leg, anchor)
            table.insert(pad.legs, { node = leg, rod = rod, foot = foot, x = x, z = z })
        end
    end
    -- šířka plošiny z rozteče nožiček (symetrické páry kolem osy X), bez duplikace v XML
    pad.width = 0
    for _, leg in ipairs(pad.legs) do
        pad.width = math.max(pad.width, math.abs(leg.x) * 2)
    end
    if pad.width <= 0 then
        pad.width = 1.5
    end
    spec.pad = pad
end

-- V obchodě (a v konfiguraci) je bedna rozložená jen z půlky: horní víko a přední stěna se rozloží do jedné řady se zadní stěnou, takže vzadu
-- stojí jedna dlouhá deska s barvou a nálepkami; boční stěny zůstanou složené a dron zůstane složený v bedně s vrtulemi podél ramen.
-- Foldable si čas skládání bere z loadedFoldAnimTime až v onPostLoad, takže stačí ho tady přepsat; koupený vlek se načítá znovu už mimo
-- obchod a začíná složený.
function SprayDronePad.openInShop(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local foldable = self.spec_foldable
    if spec.pad == nil or foldable == nil or foldable.loadedFoldAnimTime == nil then
        return
    end
    if VehiclePropertyState ~= nil and self.propertyState == VehiclePropertyState.SHOP_CONFIG then
        spec.pad.shopPose = true
        foldable.loadedFoldAnimTime = 1
    end
end

-- Hodnota 0..1: 0 = složená bedna, 1 = rozložená na nožičkách.
function SprayDronePad.getDeploy(self)
    local pad = self[SprayDroneStation.SPEC_NAME].pad
    local time = self:getFoldAnimTime()
    return math.clamp((pad.foldStart - time) / math.max(pad.foldStart - pad.foldEnd, 0.001), 0, 1)
end

function SprayDronePad.getIsStowed(self)
    local pad = self[SprayDroneStation.SPEC_NAME].pad
    return pad == nil or self:getFoldAnimTime() >= SprayDronePad.STOWED_TIME
end

function SprayDronePad.needsUpdate(self)
    local pad = self[SprayDroneStation.SPEC_NAME].pad
    return pad ~= nil and pad.settle > 0
end

---------------------------------------------------------------------------------------------------
-- plán rozložení: kde plošina stojí, jak je natočená a jak dlouhé budou nožičky

-- Poloha rozložené plošiny ve světě: kotevní bod (nehýbe se, bedna nikam nejede) a natočení kolem svislé osy (po
-- směru vleku - stejné jako u stojícího, nerozloženého vleku, počítá se z pevného rodiče, ne z animovaného anchoru).
local function getFinalPose(pad)
    local x, y, z = getWorldTranslation(pad.anchor)
    local ex, _, ez = unpack(pad.endOffset)
    local dx, _, dz = localDirectionToWorld(pad.parent, ex, 0, ez)
    local len = MathUtil.vector3Length(dx, 0, dz)
    if len > 0.001 and MathUtil.vector3Length(ex, 0, ez) > 0.001 then
        -- úhel, o který se musí lokální směr anchor -> konec otočit, aby mířil po směru ve světě (v i3d vede dozadu = -Z)
        return x, y, z, MathUtil.getYRotationFromDirection(dx, dz) - MathUtil.getYRotationFromDirection(ex, ez)
    end
    return x, y, z, 0
end

-- Vrací plán, nebo nil a důvod ("slope", "high"). Počítá se z (nehybné) polohy bedny a terénu. S force se terén
-- nezamítá (kontrola proběhla před rozložením, tady se plošina jen vyrovnává).
function SprayDronePad.plan(self, force)
    local pad = self[SprayDroneStation.SPEC_NAME].pad
    local cx, height, cz, yaw = getFinalPose(pad)
    local cosY, sinY = math.cos(yaw), math.sin(yaw)

    local function terrainAt(lx, lz)
        return getTerrainHeightAtWorldPos(g_terrainNode, cx + lx * cosY + lz * sinY, 0, cz - lx * sinY + lz * cosY)
    end

    local heights, legMax, legMin = {}, -math.huge, math.huge
    for i, leg in ipairs(pad.legs) do
        local h = terrainAt(leg.x, leg.z)
        heights[i] = h
        legMax, legMin = math.max(legMax, h), math.min(legMin, h)
    end
    if #heights == 0 then
        legMax, legMin = terrainAt(0, 0), terrainAt(0, 0)
    end
    -- obrys plošiny: podélná osa je endOffset (anchor -> konec), příčná osa kolmo na ni
    local ex, _, ez = unpack(pad.endOffset)
    local len = math.max(pad.depth, 0.001)
    local perpX, perpZ = -ez / len * pad.width * 0.5, ex / len * pad.width * 0.5
    local plateMax = -math.huge
    for _, uu in ipairs({ -1, 0, 1 }) do
        for k = 0, 4 do
            local s = k / 4
            plateMax = math.max(plateMax, terrainAt(ex * s + perpX * uu, ez * s + perpZ * uu))
        end
    end
    local lengths, longest, shortest = {}, 0, math.huge
    for i, h in ipairs(heights) do
        lengths[i] = height - h - pad.legFoot
        longest, shortest = math.max(longest, lengths[i]), math.min(shortest, lengths[i])
    end
    if not force then
        if shortest < pad.legRest or plateMax > height - SprayDronePad.PLATE_CLEARANCE then
            return nil, "high"
        end
        if legMax - legMin > pad.maxHeightDiff or longest > pad.maxLegLength then
            return nil, "slope"
        end
    end

    -- natočení: jen otočení kolem svislé osy ve světě, plošina je vždy vodorovná (vlek může stát šikmo)
    local q0 = { getQuaternion(pad.anchor) }
    setWorldRotation(pad.anchor, 0, yaw, 0)
    local qx, qy, qz, qw = getQuaternion(pad.anchor)
    setQuaternion(pad.anchor, unpack(q0))
    -- střed plošiny (anchor + polovina hloubky) a cílová poloha dronu uprostřed, v souřadnicích rodiče (pro carrier)
    local hx, hy, hz = worldToLocal(pad.parent, cx + ex * 0.5 * cosY + ez * 0.5 * sinY, height,
        cz - ex * 0.5 * sinY + ez * 0.5 * cosY)
    return { yaw = yaw, x = cx, y = height, z = cz, quat = { qx, qy, qz, qw }, legLengths = lengths,
             centerLocal = { hx, hy, hz } }
end

---------------------------------------------------------------------------------------------------
-- pohyb bedny a dronu

-- Úhel, o který se boční stěna vyklopí od svislice, aby její vnější hrana dosedla na terén vedle vleku (stěna je ve výšce čepu, délka
-- sideLength; na rovině vychází kolem 150°, na hrbolu míň, ve svahu víc). Terén se měří kousek bokem od čepu, počítá se jen v rovině
-- vleku (náklon vleku se nezapočítává).
function SprayDronePad.getSideFall(self, side)
    local pad = self[SprayDroneStation.SPEC_NAME].pad
    local wx, wy, wz = getWorldTranslation(side.node)
    local dx, _, dz = localDirectionToWorld(pad.parent, side.side, 0, 0)
    local len = MathUtil.vector3Length(dx, 0, dz)
    if len < 0.001 or g_terrainNode == nil then
        return SprayDronePad.SIDE_FALL_MAX
    end
    local reach = pad.sideLength * SprayDronePad.SIDE_REACH
    local ground = getTerrainHeightAtWorldPos(g_terrainNode, wx + dx / len * reach, 0, wz + dz / len * reach)
    local c = math.clamp((ground + SprayDronePad.SIDE_CLEARANCE - wy) / pad.sideLength, -1, 1)
    return math.clamp(math.acos(c), SprayDronePad.SIDE_FALL_MIN, SprayDronePad.SIDE_FALL_MAX)
end

-- Boční stěna: a 0..1 je průběh vyklopení (úhel roste se čtvercem, stěna padá zrychleně), fall je cílový úhel. Čep leží na vnější spodní hraně
-- stěny u lemu paluby a jeho osa je podél vleku; kladný úhel doleva míří ven, což je v i3d (Y nahoru, Z dozadu) záporné natočení kolem Z.
function SprayDronePad.applySide(self, side, fall, a)
    setRotation(side.node, 0, 0, -side.side * fall * a * a)
end

-- plan = nil: složená bedna
function SprayDronePad.applyPose(self, plan, deploy)
    local pad = self[SprayDroneStation.SPEC_NAME].pad
    local cx, cy, cz = unpack(pad.carrierPos)
    local sideEnd, foldEnd = SprayDronePad.SIDE_END, SprayDronePad.FOLD_END
    local foldLinear = math.clamp((deploy - sideEnd) / (foldEnd - sideEnd), 0, 1)
    local fold = smooth(foldLinear)
    local legShow = smooth((foldLinear - SprayDronePad.LEG_SHOW) / (1 - SprayDronePad.LEG_SHOW))
    local legs = smooth((deploy - foldEnd) / (SprayDronePad.LEGS_END - foldEnd))
    local lift = smooth((deploy - SprayDronePad.LEGS_END) / (SprayDronePad.LIFT_END - SprayDronePad.LEGS_END))
    local move = smooth((deploy - SprayDronePad.LIFT_END) / (SprayDronePad.MOVE_END - SprayDronePad.LIFT_END))
    local land = smooth((deploy - SprayDronePad.MOVE_END) / (1 - SprayDronePad.MOVE_END))

    local angle = (math.pi * 0.5) * (1 - fold)
    setRotation(pad.hingeZ, angle, 0, 0)
    setRotation(pad.hingeH, angle, 0, 0)
    setRotation(pad.hingeP, angle, 0, 0)
    local sideProgress = math.clamp(deploy / sideEnd, 0, 1)
    for _, side in ipairs(pad.sides) do
        SprayDronePad.applySide(self, side, sideProgress > 0 and SprayDronePad.getSideFall(self, side) or 0, sideProgress)
    end

    if plan ~= nil then
        local s, q = pad.stowQuat, plan.quat
        setQuaternion(pad.anchor, MathUtil.slerpQuaternion(s[1], s[2], s[3], s[4], q[1], q[2], q[3], q[4], legs))
    else
        setQuaternion(pad.anchor, unpack(pad.stowQuat))
    end
    for i, leg in ipairs(pad.legs) do
        local length = pad.legRest
        if plan ~= nil then
            length = pad.legRest + math.max(plan.legLengths[i] - pad.legRest, 0) * legs
        end
        setScale(leg.rod, 1, length / pad.legRest, 1)
        setTranslation(leg.foot, 0, -length, 0)
        local size = math.max(legShow, 0.001)
        setScale(leg.node, size, size, size)
        setVisibility(leg.node, legShow > 0)
    end

    local tx, ty, tz = cx, cy, cz
    if plan ~= nil then
        tx, ty, tz = unpack(plan.centerLocal)
        ty = ty - pad.droneSettle
    end
    setTranslation(pad.carrier, cx + (tx - cx) * move, cy + (ty - cy) * move + pad.liftHeight * lift * (1 - land),
        cz + (tz - cz) * move)
    -- dron se po cestě srovná do roviny plošiny: na svahu stojí vlek šikmo, plošina je vodorovná, takže carrier nejde otočit jen o
    -- yaw v souřadnicích vleku - cílová rotace se vezme ve světě (jen yaw plošiny minus droneYaw) a prolne se od složené polohy
    local q = pad.carrierQuat
    if plan ~= nil and move > 0 then
        setWorldRotation(pad.carrier, 0, plan.yaw - pad.droneYaw, 0)
        local qx, qy, qz, qw = getQuaternion(pad.carrier)
        setQuaternion(pad.carrier, MathUtil.slerpQuaternion(q[1], q[2], q[3], q[4], qx, qy, qz, qw, move))
    else
        setQuaternion(pad.carrier, q[1], q[2], q[3], q[4])
    end
end

-- Z onUpdate vleku. Pohyb se přepočítá jen při změně času skládání nebo po načtení (vlek se do světa umístí až po onLoad,
-- proto několik snímků po načtení).
function SprayDronePad.update(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local pad = spec.pad
    if pad == nil then
        return
    end
    local time = self:getFoldAnimTime()
    local key = pad.appliedTime
    if pad.settle > 0 then
        pad.settle = pad.settle - 1
        key = nil
    end
    if key == time then
        return
    end
    pad.appliedTime = time
    local deploy = SprayDronePad.getDeploy(self)
    if deploy <= 0 then
        SprayDronePad.applyPose(self, nil, 0)
        if pad.shopPose then
            setRotation(pad.hingeH, 0, 0, 0)
            setRotation(pad.hingeP, 0, 0, 0)
        end
        return
    end
    SprayDronePad.applyPose(self, SprayDronePad.plan(self, true), deploy)
end

---------------------------------------------------------------------------------------------------
-- kontrola před rozložením

local overlapProbe = { vehicle = nil, hit = false }

function overlapProbe.callback(probe, nodeId)
    if nodeId ~= 0 and getHasClassId(nodeId, ClassIds.SHAPE) and not getHasTrigger(nodeId) then
        local object = g_currentMission:getNodeObject(nodeId)
        local vehicle = probe.vehicle
        local own = object == vehicle
            or (object ~= nil and object.getRootVehicle ~= nil and object:getRootVehicle() == vehicle:getRootVehicle())
        if not own then
            probe.hit = true
            return false
        end
    end
    return true
end

local function isBoxBlocked(vehicle, x, y, z, rx, ry, rz, ex, ey, ez)
    overlapProbe.vehicle = vehicle
    overlapProbe.hit = false
    overlapBox(x, y, z, rx, ry, rz, ex, ey, ez, "callback", overlapProbe, SprayDronePad.OVERLAP_MASK, true, true, false, true)
    overlapProbe.vehicle = nil
    return overlapProbe.hit
end

-- Střed celé rozložené plošiny ve světě.
local function getPlateCenter(pad, plan)
    local ex, _, ez = unpack(pad.endOffset)
    local cosY, sinY = math.cos(plan.yaw), math.sin(plan.yaw)
    return plan.x + ex * 0.5 * cosY + ez * 0.5 * sinY, plan.z - ex * 0.5 * sinY + ez * 0.5 * cosY
end

-- Místo rozložené plošiny s dronem (celá je za vlekem) a prostor nad složenou bednou pro vzlet dronu (vlastní vlek
-- se ignoruje).
function SprayDronePad.isBlocked(self, plan)
    local pad = self[SprayDroneStation.SPEC_NAME].pad
    local m = SprayDronePad.MARGIN
    local px, pz = getPlateCenter(pad, plan)
    local from = 0.10
    local half = (pad.checkHeight + from) * 0.5
    if isBoxBlocked(self, px, plan.y - from + half, pz, 0, plan.yaw, 0,
        pad.width * 0.5 + m, half, pad.depth * 0.5 + m) then
        return true
    end
    local sx, sy, sz = unpack(pad.stowPos)
    local up = (pad.liftHeight + SprayDronePad.CORRIDOR_HEIGHT) * 0.5
    local wx, wy, wz = localToWorld(pad.parent, sx, sy + 0.05 + up, sz)
    local rx, ry, rz = getWorldRotation(pad.parent)
    return isBoxBlocked(self, wx, wy, wz, rx, ry, rz, pad.width * 0.5 + m, up, pad.width * 0.5 + m)
end

-- Dosáhne hadice z navíječe na vleku k hrdlu dronu na rozložené plošině? Délka klidové hadice (hladká křivka přes body Lay,
-- stejná, jakou kreslí SprayDroneService) bez pevného úseku do Lay3 a bez rovného nájezdu do koncovky je volná část; potřebná délka
-- je vzdálenost pevného konce od hrdla dronu (na středu rozložené plošiny, droneSettle níž) s rezervou na prověšení a oblouk.
function SprayDronePad.hoseReaches(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local pad = spec.pad
    local hose = spec.hose
    if hose == nil or hose.port == nil then
        return true
    end
    local anchorNode = hose.lay[SprayDroneStation.HOSE_FIXED_LAY]
    if anchorNode == nil then
        return true
    end
    local rest = SprayDroneStation.getHoseRestLine(hose)
    local free = (rest.length - SprayDroneStation.HOSE_NOZZLE_LEAD - (rest.fixed or 0)) * 0.97
    local ax, ay, az = worldToLocal(pad.parent, getWorldTranslation(anchorNode))
    local plan = SprayDronePad.plan(self, true)
    local px, py, pz = unpack(plan.centerLocal)
    local _, portY = worldToLocal(pad.parent, getWorldTranslation(hose.port))
    py = py - pad.droneSettle + (portY - pad.carrierPos[2])
    local need = MathUtil.vector3Length(px - ax, py - ay, pz - az) * SprayDronePad.HOSE_SLACK + SprayDronePad.HOSE_ARC
    return need <= free
end

-- Může se vlek rozložit? Vrací true, nebo false a text varování.
function SprayDronePad.checkDeploy(self)
    local pad = self[SprayDroneStation.SPEC_NAME].pad
    if pad == nil or self:getFoldAnimTime() < SprayDronePad.STOWED_TIME then
        return true
    end
    local plan, reason = SprayDronePad.plan(self)
    if plan == nil then
        return false, g_i18n:getText(reason == "high" and "sdt_warning_padHigh" or "sdt_warning_padSlope")
    end
    if SprayDronePad.isBlocked(self, plan) then
        return false, g_i18n:getText("sdt_warning_padBlocked")
    end
    if not SprayDronePad.hoseReaches(self) then
        return false, g_i18n:getText("sdt_warning_padHose")
    end
    return true
end

-- Obrys rozložené plošiny ve světě na složeném vleku: zelený, jde-li to, červený, když ne.
function SprayDronePad.drawPreview(self)
    local pad = self[SprayDroneStation.SPEC_NAME].pad
    if pad == nil or not SprayDronePad.getIsStowed(self) then
        return
    end
    local r, g, b = 0.1, 0.9, 0.2
    local plan = SprayDronePad.plan(self)
    if plan == nil then
        r, g, b = 0.95, 0.15, 0.1
        plan = SprayDronePad.plan(self, true)
    else
        if pad.previewCheckTime == nil or g_time - pad.previewCheckTime > SprayDronePad.PREVIEW_CHECK_MS then
            pad.previewCheckTime = g_time
            pad.previewBlocked = SprayDronePad.isBlocked(self, plan) or not SprayDronePad.hoseReaches(self)
        end
        if pad.previewBlocked then
            r, g, b = 0.95, 0.15, 0.1
        end
    end
    local x, z = getPlateCenter(pad, plan)
    local hx, hz = pad.width * 0.5, pad.depth * 0.5
    local cosY, sinY = math.cos(plan.yaw), math.sin(plan.yaw)
    local corners = {}
    for i, c in ipairs({ { -hx, -hz }, { hx, -hz }, { hx, hz }, { -hx, hz } }) do
        local cornerX = x + c[1] * cosY + c[2] * sinY
        local cornerZ = z - c[1] * sinY + c[2] * cosY
        corners[i] = { cornerX, getTerrainHeightAtWorldPos(g_terrainNode, cornerX, 0, cornerZ) + 0.06, cornerZ }
    end
    for i = 1, 4 do
        local a, c = corners[i], corners[i % 4 + 1]
        drawDebugLine(a[1], a[2], a[3], r, g, b, c[1], c[2], c[3], r, g, b)
    end
end
