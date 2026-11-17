-- Tažné hadice na vodu (velký vlek Max / Middle a přenosná pumpa): hráč u spojky (R) vezme konec hadice, odnese ho a R ho připojí. Každé vozidlo má
-- jednu nebo víc hadic (spec.hoses), každá má vlastní řetěz článků, koncovku a spojky:
--   vlek (jedna hadice, pořadí spojek podle konfigurace): ke ventilu vodní nádrže patří voda (IBC, cisterna, vodní vlek), ke vstupu nádobky jemné vápno
--     z výstupu mlýnkového vozíku (mlýn musí běžet; ventil vstupu se otevře sám při připojení hadice);
--   pumpa (dvě hadice): "inlet" = VSTUP, podle ručně přepnutého režimu pumpy (SprayDronePump.pondMode) "water" (spojka Storz, konec na výstup IBC / cisterny)
--     nebo "pond" (sací koš, pustí se do vody); "sink" = VÝSTUP (konec na vodní ventil vleku).
-- R u spojky nebo u druhého konce hadici odpojí a zasune. Tvar hadice (obcházení vozidel, ležení na zemi, koncovka) dává SprayDroneHoseLib.
--
-- Stav (vytažená hadice, nesený konec, zdroj, kohout) rozhoduje server a jde klientům ve stavu vozidla; příkazy jdou eventem.

if SprayDroneHoseLib == nil then
    source(g_currentModDirectory .. "scripts/SprayDroneHoseLib.lua")
end
source(g_currentModDirectory .. "scripts/events/SprayDroneWaterHoseEvent.lua")

SprayDroneWaterHose = {}
SprayDroneWaterHose.MOD_NAME = g_currentModName
SprayDroneWaterHose.SPEC_NAME = string.format("spec_%s.sprayDroneWaterHose", g_currentModName)

SprayDroneWaterHose.CMD_TAKE = 1
SprayDroneWaterHose.CMD_DRAG = 2
SprayDroneWaterHose.CMD_DROP = 3
SprayDroneWaterHose.CMD_CONNECT = 4
SprayDroneWaterHose.CMD_BITS = 3
SprayDroneWaterHose.HOSE_BITS = 2              -- číslo hadice v příkazu (nejvýš 4 hadice na vozidlo)

SprayDroneWaterHose.PORT_DISTANCE = 1.9        -- hráč nejvýš tak daleko od ventilu, aby z něj mohl hadici vzít nebo ji odpojit
SprayDroneWaterHose.SOURCE_RADIUS = 1.1        -- konec hadice nejvýš tak daleko od karoserie zdroje, aby šel připojit
SprayDroneWaterHose.SINK_RADIUS = 2.0          -- konec výstupní hadice nejvýš tak daleko od ventilu vleku, aby šel připojit (ventily jsou na palubě, hráč stojí u boku vleku na zemi)
SprayDroneWaterHose.UNPLUG_DISTANCE = 2.0      -- hráč nejvýš tak daleko od připojeného konce, aby ho mohl odpojit
SprayDroneWaterHose.DRAG_INTERVAL = 100        -- jak často držitel posílá serveru polohu konce hadice (ms)
SprayDroneWaterHose.RESOLVE_MS = 15000         -- po načtení hry tak dlouho se hledá zdroj, ke kterému byla hadice připojená
SprayDroneWaterHose.VALVE_TIME = 0.35          -- otočení páky kohoutu vstupu (s)
SprayDroneWaterHose.MIN_LITERS = 0.001
SprayDroneWaterHose.OUTLET_REACH = 0.5         -- konec hadice nejvýš o tolik dál od vypouštěcího uzlu zdroje, než je SOURCE_RADIUS
SprayDroneWaterHose.OUTLET_HEIGHT = 0.3        -- výška výpustě nad zemí u zdroje bez vypouštěcího uzlu (vanilla IBC: kohout dole u rámu)
SprayDroneWaterHose.OUTLET_SNAP = 1.3          -- nejvýš tak daleko od vypouštěcího uzlu smí ležet bod dotyku na povrchu zdroje (m)
SprayDroneWaterHose.OUTLET_MAX_HEIGHT = 0.8    -- vypouštěcí uzel výš nad počátkem vozidla se nebere za výstup (kupole cisterny): hadice jde na bok při zemi
SprayDroneWaterHose.SURFACE_MASK = (CollisionFlag.VEHICLE or 0) + (CollisionFlag.DYNAMIC_OBJECT or 0) + (CollisionFlag.DEFAULT or 0)
    + (CollisionFlag.TRAILER or 0)
SprayDroneWaterHose.POND_ARG = 15              -- hodnota arg v příkazu CONNECT: konec hadice leží ve vodě (rybník), ne na vozidle
SprayDroneWaterHose.TANK_ARG = 14              -- totéž u výstupní hadice pumpy: konec leží na libovolné cizí nádrži (cisterna), ne na ventilu vleku
SprayDroneWaterHose.POND_CHECK_MS = 500        -- jak často server kontroluje, jestli je koš pořád ve vodě
SprayDroneWaterHose.POND_DEPTH = 0.15          -- výchozí nejmenší hloubka vody u koše (m)
SprayDroneWaterHose.POND_REACH = 1.5           -- koš se hodí do vody nejvýš tak daleko od ruky (m)

local L = SprayDroneHoseLib

local function getSpec(self)
    return self[SprayDroneWaterHose.SPEC_NAME]
end

local function getMappedNode(self, name)
    local mapping = self.i3dMappings ~= nil and self.i3dMappings[name] or nil
    if type(mapping) == "table" then
        return mapping.nodeId
    end
    return nil
end

function SprayDroneWaterHose.prerequisitesPresent(specializations)
    return SpecializationUtil.hasSpecialization(FillUnit, specializations)
end

function SprayDroneWaterHose.initSpecialization()
    local schema = Vehicle.xmlSchema
    schema:setXMLSpecializationType("SprayDroneWaterHose")
    local key = "vehicle.sprayDroneWaterHose"
    -- jedna hadice (vlek): všechny spojky v <ports>
    schema:register(XMLValueType.FLOAT, key .. "#hoseLength", "Délka hadice (m)", 12)
    schema:register(XMLValueType.FLOAT, key .. "#rate", "Průtok vody hadicí (l/s)", 12)
    schema:register(XMLValueType.NODE_INDEX, key .. ".nodes#hoseEnd", "Koncovka vytažené hadice")
    schema:register(XMLValueType.STRING, key .. ".nodes#segmentPrefix", "Prefix mapovaných uzlů článků hadice", "waterHoseSeg")
    schema:register(XMLValueType.INT, key .. ".nodes#segmentCount", "Počet článků hadice", 72)
    schema:register(XMLValueType.NODE_INDEX, key .. ".ports.port(?)#node", "Konec výpustního ventilu vodní nádrže (hadice se bere odtud)")
    -- víc hadic (pumpa): každá se svým řetězem článků a spojkami
    local hoseKey = key .. ".hoses.hose(?)"
    schema:register(XMLValueType.FLOAT, hoseKey .. "#hoseLength", "Délka hadice (m)", 12)
    schema:register(XMLValueType.FLOAT, hoseKey .. "#rate", "Průtok vody hadicí (l/s)", 12)
    schema:register(XMLValueType.BOOL, hoseKey .. "#lime", "Hadice jen pro vstup na jemné vápno (limeInlet vleku)", false)
    schema:register(XMLValueType.NODE_INDEX, hoseKey .. "#hoseEnd", "Koncovka vytažené hadice")
    schema:register(XMLValueType.NODE_INDEX, hoseKey .. "#strainerEnd", "Koncovka se sacím košem místo hoseEnd, když je vstup pumpy v režimu rybník")
    schema:register(XMLValueType.STRING, hoseKey .. "#segmentPrefix", "Prefix mapovaných uzlů článků hadice", "waterHoseSeg")
    schema:register(XMLValueType.INT, hoseKey .. "#segmentCount", "Počet článků hadice", 72)
    schema:register(XMLValueType.NODE_INDEX, hoseKey .. ".port(?)#node", "Spojka, ze které hadice vede")
    schema:register(XMLValueType.STRING, hoseKey .. ".port(?)#kind", "water (vstup z IBC / cisterny), pond (vstup z rybníka), inlet (vstup pumpy: water nebo pond podle režimu), sink (výstup na vlek)", "water")
    schema:setXMLSpecializationType()

    local savegame = Vehicle.xmlSchemaSavegame
    local saveKey = string.format("vehicles.vehicle(?).%s.sprayDroneWaterHose.hose(?)", SprayDroneWaterHose.MOD_NAME)
    savegame:register(XMLValueType.INT, saveKey .. "#port", "Číslo ventilu, ze kterého hadice vede")
    savegame:register(XMLValueType.STRING, saveKey .. "#sourceId", "uniqueId vozidla se zdrojem")
    savegame:register(XMLValueType.VECTOR_3, saveKey .. "#sourcePos", "Poloha konce hadice na zdroji (souřadnice zdroje; u rybníka světové)")
    savegame:register(XMLValueType.VECTOR_2, saveKey .. "#sourceDir", "Směr do zdroje (souřadnice zdroje, vodorovně x z; u rybníka světový)")
    savegame:register(XMLValueType.INT, saveKey .. "#targetPort", "Číslo ventilu vleku, na který vede výstupní hadice")
    savegame:register(XMLValueType.BOOL, saveKey .. "#pond", "Koš hadice leží v rybníku")
end

function SprayDroneWaterHose.registerFunctions(vehicleType)
    SpecializationUtil.registerFunction(vehicleType, "sprayDroneWaterHoseCommand", SprayDroneWaterHose.command)
end

function SprayDroneWaterHose.registerEventListeners(vehicleType)
    for _, name in ipairs({ "onLoad", "onDelete", "onUpdate", "onReadStream", "onWriteStream", "onReadUpdateStream", "onWriteUpdateStream" }) do
        SpecializationUtil.registerEventListener(vehicleType, name, SprayDroneWaterHose)
    end
end

local function newHose(self, index, def)
    local h = { index = index, hoseLength = math.max(def.hoseLength, 1), rate = math.max(def.rate, 0.01), hoseEnd = def.hoseEnd, storzEnd = def.hoseEnd,
        strainerEnd = def.strainerEnd, ports = def.ports, lime = def.lime == true, segments = {} }
    for i = 1, def.segmentCount do
        local node = getMappedNode(self, def.segmentPrefix .. i)
        if node ~= nil then
            table.insert(h.segments, node)
        end
    end
    h.out = false
    h.port = 1
    h.held = false
    h.localHold = false
    h.holdX, h.holdY, h.holdZ = 0, 0, 0
    h.holdDX, h.holdDY, h.holdDZ = 0, 0, 1
    h.source = nil
    h.targetPort = nil
    h.pond = false
    h.srcX, h.srcY, h.srcZ, h.srcDX, h.srcDZ = 0, 0, 0, 0, 1
    h.valveOpen = false
    h.valveAnim = 0
    h.dragTimer = 0
    h.shown = false
    h.warned = false
    h.pondTimer = 0
    return h
end

function SprayDroneWaterHose:onLoad(savegame)
    local spec = getSpec(self)
    local xml = self.xmlFile
    local key = "vehicle.sprayDroneWaterHose"
    spec.hoses = {}
    xml:iterate(key .. ".hoses.hose", function(_, hoseKey)
        local ports = {}
        xml:iterate(hoseKey .. ".port", function(_, portKey)
            local node = xml:getValue(portKey .. "#node", nil, self.components, self.i3dMappings)
            if node ~= nil then
                table.insert(ports, { node = node, kind = xml:getValue(portKey .. "#kind", "water") })
            end
        end)
        table.insert(spec.hoses, newHose(self, #spec.hoses + 1, {
            hoseLength = xml:getValue(hoseKey .. "#hoseLength", 12), rate = xml:getValue(hoseKey .. "#rate", 12),
            hoseEnd = xml:getValue(hoseKey .. "#hoseEnd", nil, self.components, self.i3dMappings),
            strainerEnd = xml:getValue(hoseKey .. "#strainerEnd", nil, self.components, self.i3dMappings),
            segmentPrefix = xml:getValue(hoseKey .. "#segmentPrefix", "waterHoseSeg"), segmentCount = xml:getValue(hoseKey .. "#segmentCount", 72),
            lime = xml:getValue(hoseKey .. "#lime", false), ports = ports }))
    end)
    if #spec.hoses == 0 then
        local ports = {}
        xml:iterate(key .. ".ports.port", function(_, portKey)
            local node = xml:getValue(portKey .. "#node", nil, self.components, self.i3dMappings)
            if node ~= nil then
                table.insert(ports, { node = node, kind = "water" })
            end
        end)
        table.insert(spec.hoses, newHose(self, 1, {
            hoseLength = xml:getValue(key .. "#hoseLength", 12), rate = xml:getValue(key .. "#rate", 12),
            hoseEnd = xml:getValue(key .. ".nodes#hoseEnd", nil, self.components, self.i3dMappings),
            segmentPrefix = xml:getValue(key .. ".nodes#segmentPrefix", "waterHoseSeg"), segmentCount = xml:getValue(key .. ".nodes#segmentCount", 72),
            ports = ports }))
    end
    spec.dirtyFlag = self:getNextDirtyFlag()
    for _, h in ipairs(spec.hoses) do
        SprayDroneWaterHose.showChain(h, false)
    end

    if savegame ~= nil and not savegame.resetVehicles and self.isServer then
        for i, h in ipairs(spec.hoses) do
            local saveKey = string.format("%s.%s.sprayDroneWaterHose.hose(%d)", savegame.key, SprayDroneWaterHose.MOD_NAME, i - 1)
            local sourceId = savegame.xmlFile:getValue(saveKey .. "#sourceId")
            local pond = savegame.xmlFile:getValue(saveKey .. "#pond", false)
            if sourceId ~= nil or pond then
                h.pendingId = sourceId
                h.pendingPond = pond
                h.pendingPort = savegame.xmlFile:getValue(saveKey .. "#port", 1)
                h.pendingTarget = savegame.xmlFile:getValue(saveKey .. "#targetPort")
                h.pendingPos = { savegame.xmlFile:getValue(saveKey .. "#sourcePos", "0 0 0") }
                h.pendingDir = { savegame.xmlFile:getValue(saveKey .. "#sourceDir", "0 1") }
                h.pendingTime = SprayDroneWaterHose.RESOLVE_MS
            end
        end
    end

    if self.isClient and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        spec.activatable = SprayDroneWaterHoseActivatable.new(self)
        g_currentMission.activatableObjectsSystem:addActivatable(spec.activatable)
    end
end

function SprayDroneWaterHose:saveToXMLFile(xmlFile, key, usedModNames)
    local spec = getSpec(self)
    for i, h in ipairs(spec.hoses) do
        local source = h.source
        local hoseKey = string.format("%s.hose(%d)", key, i - 1)
        if h.out and not h.held and (h.pond or (source ~= nil and not source.isDeleted and source.getUniqueId ~= nil)) then
            xmlFile:setValue(hoseKey .. "#port", h.port)
            xmlFile:setValue(hoseKey .. "#sourcePos", h.srcX, h.srcY, h.srcZ)
            xmlFile:setValue(hoseKey .. "#sourceDir", h.srcDX, h.srcDZ)
            if h.pond then
                xmlFile:setValue(hoseKey .. "#pond", true)
            else
                xmlFile:setValue(hoseKey .. "#sourceId", source:getUniqueId())
                if h.targetPort ~= nil then
                    xmlFile:setValue(hoseKey .. "#targetPort", h.targetPort)
                end
            end
        end
    end
end

function SprayDroneWaterHose:onDelete()
    local spec = getSpec(self)
    if spec == nil then
        return
    end
    if spec.activatable ~= nil and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        g_currentMission.activatableObjectsSystem:removeActivatable(spec.activatable)
    end
    spec.activatable = nil
end

---------------------------------------------------------------------------------------------------
-- síť

local function writeHose(h, streamId)
    streamWriteBool(streamId, h.out)
    streamWriteUIntN(streamId, h.port, 4)
    streamWriteBool(streamId, h.valveOpen)
    streamWriteBool(streamId, h.pond)
    streamWriteUIntN(streamId, h.targetPort or 0, 4)
    if streamWriteBool(streamId, h.held) then
        for _, v in ipairs({ h.holdX, h.holdY, h.holdZ, h.holdDX, h.holdDY, h.holdDZ }) do
            streamWriteFloat32(streamId, v)
        end
    end
    if streamWriteBool(streamId, h.source ~= nil or h.pond) then
        if streamWriteBool(streamId, h.source ~= nil) then
            NetworkUtil.writeNodeObject(streamId, h.source)
        end
        for _, v in ipairs({ h.srcX, h.srcY, h.srcZ, h.srcDX, h.srcDZ }) do
            streamWriteFloat32(streamId, v)
        end
    end
end

local function readHose(h, streamId)
    h.out = streamReadBool(streamId)
    h.port = streamReadUIntN(streamId, 4)
    h.valveOpen = streamReadBool(streamId)
    h.pond = streamReadBool(streamId)
    local targetPort = streamReadUIntN(streamId, 4)
    h.targetPort = targetPort ~= 0 and targetPort or nil
    h.held = streamReadBool(streamId)
    if h.held then
        local v = {}
        for i = 1, 6 do
            v[i] = streamReadFloat32(streamId)
        end
        if not h.localHold then
            h.holdX, h.holdY, h.holdZ, h.holdDX, h.holdDY, h.holdDZ = unpack(v)
        end
    else
        h.localHold = false
    end
    h.source = nil
    if streamReadBool(streamId) then
        if streamReadBool(streamId) then
            h.source = NetworkUtil.readNodeObject(streamId)
        end
        h.srcX, h.srcY, h.srcZ, h.srcDX, h.srcDZ = streamReadFloat32(streamId), streamReadFloat32(streamId), streamReadFloat32(streamId),
            streamReadFloat32(streamId), streamReadFloat32(streamId)
    end
end

local function writeState(self, streamId)
    for _, h in ipairs(getSpec(self).hoses) do
        writeHose(h, streamId)
    end
end

local function readState(self, streamId)
    for _, h in ipairs(getSpec(self).hoses) do
        readHose(h, streamId)
    end
    self:raiseActive()
end

function SprayDroneWaterHose:onWriteStream(streamId, connection)
    writeState(self, streamId)
end

function SprayDroneWaterHose:onReadStream(streamId, connection)
    readState(self, streamId)
end

function SprayDroneWaterHose:onWriteUpdateStream(streamId, connection, dirtyMask)
    if not connection:getIsServer() then
        local spec = getSpec(self)
        if streamWriteBool(streamId, bit32.band(dirtyMask, spec.dirtyFlag) ~= 0) then
            writeState(self, streamId)
        end
    end
end

function SprayDroneWaterHose:onReadUpdateStream(streamId, timestamp, connection)
    if connection:getIsServer() and streamReadBool(streamId) then
        readState(self, streamId)
    end
end

---------------------------------------------------------------------------------------------------
-- spojky, vstup na koncentrát a zdroje

-- Je celý řetěz rodičů uzlu viditelný? Ventily nepoužité konfigurace nádrží jsou skryté s nádrží.
local function isNodeVisible(node)
    while node ~= nil and node ~= 0 do
        if not getVisibility(node) then
            return false
        end
        node = getParent(node)
    end
    return true
end

-- Všechny spojky hadice vozidla: u vleku ventily vodních nádrží (kind water, číslo nádrže z vleku) a vstup nádobky na koncentrát (kind lime,
-- s kohoutem; pořadí: nejdřív ventily z XML, vstup nakonec), u pumpy spojka hadice (water / pond / sink, nádrž s vodou v pumpě; vstup pumpy je podle
-- režimu water nebo pond a má příznak inlet).
function SprayDroneWaterHose.getPorts(self, hoseIndex)
    local spec = getSpec(self)
    local hose = spec.hoses[hoseIndex or 1]
    local ports = {}
    local station = self[SprayDroneStation.SPEC_NAME]
    local pump = self[SprayDronePump.SPEC_NAME]
    local unit = station ~= nil and station.fillUnitIndex or pump ~= nil and pump.waterUnit or 1
    for i, p in ipairs(hose.ports) do
        local inlet = p.kind == "inlet"
        local kind = p.kind
        if inlet then
            kind = (pump ~= nil and pump.pondMode) and "pond" or "water"
        end
        ports[i] = { node = p.node, kind = kind, inlet = inlet, fillUnitIndex = unit, fillType = FillType.WATER }
    end
    if hose.lime then
        local inlet = SprayDroneStation.getLimeInlet(self)
        if inlet ~= nil then
            ports[#ports + 1] = { node = inlet.node, kind = "lime", fillUnitIndex = inlet.fillUnitIndex, fillType = inlet.fillType,
                valveNode = inlet.valveNode, valveOpenAngle = inlet.valveOpenAngle }
        end
    end
    return ports
end

-- Spojky aktuální konfigurace (skryté nádrže se vynechají): seznam {index, node, port}.
function SprayDroneWaterHose.getActivePorts(self, hoseIndex)
    local list = {}
    for index, port in ipairs(SprayDroneWaterHose.getPorts(self, hoseIndex)) do
        if entityExists(port.node) and isNodeVisible(port.node) then
            list[#list + 1] = { index = index, node = port.node, port = port }
        end
    end
    return list
end

-- Číslo nádrže se zdrojovou vodou ve vozidle, nebo nil. Z pumpy jde vodu brát jen její vlastní výstupní hadicí.
local function getWaterUnit(vehicle)
    if vehicle.spec_fillUnit == nil or vehicle.getFillUnitFillType == nil or vehicle[SprayDronePump.SPEC_NAME] ~= nil then
        return nil
    end
    for index = 1, #vehicle.spec_fillUnit.fillUnits do
        if vehicle:getFillUnitFillType(index) == FillType.WATER and vehicle:getFillUnitFillLevel(index) > 0.001 then
            return index
        end
    end
    return nil
end

-- Číslo nádrže cizího vozidla (bez vodních ventilů a pumpy), do které jde výstupní hadicí pumpy napouštět vodu: bere vodu, je v ní místo a je prázdná nebo s vodou.
local function getWaterSinkUnit(vehicle)
    if vehicle.spec_fillUnit == nil or vehicle.getFillUnitSupportsFillType == nil or vehicle[SprayDronePump.SPEC_NAME] ~= nil
        or vehicle[SprayDroneWaterHose.SPEC_NAME] ~= nil then
        return nil
    end
    for index = 1, #vehicle.spec_fillUnit.fillUnits do
        if vehicle:getFillUnitSupportsFillType(index, FillType.WATER) and vehicle:getFillUnitCapacity(index) > 100
            and vehicle:getFillUnitFreeCapacity(index) > SprayDroneWaterHose.MIN_LITERS
            and (vehicle:getFillUnitFillLevel(index) < SprayDroneWaterHose.MIN_LITERS or vehicle:getFillUnitFillType(index) == FillType.WATER) then
            return index
        end
    end
    return nil
end

local function getDischargeNodes(vehicle)
    local spec = vehicle.spec_dischargeable
    return spec ~= nil and spec.dischargeNodes or nil
end

-- Je vypouštěcí uzel dole (do OUTLET_MAX_HEIGHT nad počátkem vozidla)? Uzly nahoře (poklop, kupole) jsou pro hráče s hadicí nedosažitelné.
local function isLowNode(vehicle, node)
    if node == nil or not entityExists(node) then
        return false
    end
    local _, y = localToLocal(node, vehicle.rootNode, 0, 0, 0)
    return y <= SprayDroneWaterHose.OUTLET_MAX_HEIGHT
end

-- Výstupy zdroje, na které jde hadice: jen nízké vypouštěcí uzly (Dischargeable); zdroj bez nich (cisterna s uzlem nahoře) přijme hadici kamkoli na karoserii.
local function getOutletNodes(vehicle)
    local list = {}
    for _, dn in ipairs(getDischargeNodes(vehicle) or {}) do
        if isLowNode(vehicle, dn.node) then
            table.insert(list, dn.node)
        end
    end
    return list
end

-- Má zdroj výstup (nízký vypouštěcí uzel nebo pojmenovaný ventil)? Pak hadice jde jen na něj.
local function hasDischargeNodes(vehicle)
    return #getOutletNodes(vehicle) > 0
end

-- Nejbližší výstup zdroje k bodu (x, y, z) do vzdálenosti reach: uzel a vzdálenost, jinak nil.
local function findDischargeNode(vehicle, x, y, z, reach)
    local best, bestDistance
    for _, node in ipairs(getOutletNodes(vehicle)) do
        local nx, ny, nz = getWorldTranslation(node)
        local distance = MathUtil.vector3Length(x - nx, y - ny, z - nz)
        if distance <= reach and (bestDistance == nil or distance < bestDistance) then
            best, bestDistance = node, distance
        end
    end
    return best, bestDistance
end

local surfaceProbe = {}

function surfaceProbe:callback(hitId, x, y, z)
    local node = hitId
    while node ~= nil and node ~= 0 do
        if g_currentMission:getNodeObject(node) == self.target then
            self.hit, self.x, self.y, self.z = true, x, y, z
            break
        end
        node = getParent(node)
    end
    return false
end

-- Skutečný povrch zdroje: vodorovný paprsek z (sx, sz) k (tx, tz) v zadaných výškách (světové y); vrací bod dotyku a směr paprsku (do vozidla),
-- nebo nil, když paprsek zdroj nezasáhne. Koncovka hadice tak vždy sedí na karoserii, ne ve vzduchu.
local function findSurface(vehicle, sx, sz, tx, tz, heights)
    local dx, dz = tx - sx, tz - sz
    local length = math.sqrt(dx * dx + dz * dz)
    if length < 0.01 then
        return nil
    end
    dx, dz = dx / length, dz / length
    surfaceProbe.target = vehicle
    for _, y in ipairs(heights) do
        surfaceProbe.hit = false
        raycastClosest(sx, y, sz, dx, 0, dz, length, "callback", surfaceProbe, SprayDroneWaterHose.SURFACE_MASK)
        if surfaceProbe.hit then
            return surfaceProbe.x, surfaceProbe.y, surfaceProbe.z, dx, dz
        end
    end
    return nil
end

-- Nejbližší bod na těle zdroje k bodu (x, z) do vzdálenosti radius od jeho obdélníku (v.size): vzdálenost, bod připojení (x, y, z) a vodorovný
-- směr do vozidla; nil, když je zdroj dál. Bod se upřesní paprskem na skutečný povrch při zemi, jinak zůstane na obdélníku.
local function snapToBody(v, x, z, radius)
    local box = L.boxOf(v)
    if box == nil then
        return nil
    end
    local dx, dz = x - box.x, z - box.z
    local u, w = dx * box.ux + dz * box.uz, dx * box.wx + dz * box.wz
    local cu, cw = math.clamp(u, -box.hu, box.hu), math.clamp(w, -box.hw, box.hw)
    local distance = MathUtil.vector2Length(u - cu, w - cw)
    if distance > radius then
        return nil
    end
    local su, sw, nu, nw = cu, cw, 0, 0
    if distance < 1e-4 then
        if box.hu - math.abs(u) < box.hw - math.abs(w) then
            su, nu = (u >= 0 and 1 or -1) * box.hu, u >= 0 and 1 or -1
        else
            sw, nw = (w >= 0 and 1 or -1) * box.hw, w >= 0 and 1 or -1
        end
    else
        nu, nw = u - cu, w - cw
        local l = MathUtil.vector2Length(nu, nw)
        nu, nw = nu / l, nw / l
    end
    local bx, bz = box.x + su * box.ux + sw * box.wx, box.z + su * box.uz + sw * box.wz
    local ox, oz = nu * box.ux + nw * box.wx, nu * box.uz + nw * box.wz
    local floor = L.floorAt(bx, bz)
    local height = v.size ~= nil and v.size.height or 1
    local by = floor + math.min(SprayDroneWaterHose.OUTLET_HEIGHT, math.max(height - 0.1, 0.15))
    local ys = {}
    for _, h in ipairs({ SprayDroneWaterHose.OUTLET_HEIGHT, 0.5, 0.7, 0.9, 1.2, 1.6 }) do
        table.insert(ys, floor + h)
    end
    local px, py, pz, pdx, pdz = findSurface(v, bx + ox * 0.6, bz + oz * 0.6, box.x, box.z, ys)
    if px ~= nil then
        return distance, px, py, pz, pdx, pdz
    end
    return distance, bx, by, bz, -ox, -oz
end

-- Zdroj jemného vápna (kind lime): mlýnek (SprayDroneMill) nebo násypka (SprayDroneHopper). Oba mají getOutlet, isRunning, markPumping a markOutletUsed;
-- outlet.closed = ventil mlýnku je na výsypné rouře, hadice zůstane připojená, ale nic nedostane.
local function getLimeModule(vehicle)
    if vehicle[SprayDroneMill.SPEC_NAME] ~= nil then
        return SprayDroneMill
    end
    if SprayDroneHopper ~= nil and vehicle[SprayDroneHopper.SPEC_NAME] ~= nil then
        return SprayDroneHopper
    end
    return nil
end

-- Nejbližší zdroj podle druhu spojky (kind water: vozidlo s vodou; kind lime: výstup mlýnku nebo násypky, i prázdný) k bodu (x, y, z). Vrací vozidlo
-- a bod připojení se směrem do vozidla (souřadnice světa): u vody výstup zdroje (vypouštěcí uzel, jinak bok těsně nad zemí), u vápna čelo spojky výstupu.
function SprayDroneWaterHose.findSourceAt(self, x, y, z, radius, kind)
    local best, bestDistance, bx, by, bz, bdx, bdz, bestPush
    local canPush = kind == "water" and self[SprayDronePump.SPEC_NAME] == nil
    local vehicles = g_currentMission.vehicleSystem ~= nil and g_currentMission.vehicleSystem.vehicles or {}
    for _, v in ipairs(vehicles) do
        if v ~= self and not v.isDeleted and v.rootNode ~= nil and entityExists(v.rootNode)
            and g_currentMission.accessHandler:canFarmAccess(self:getOwnerFarmId(), v) then
            if kind == "lime" then
                local module = getLimeModule(v)
                local outlet = module ~= nil and module.getOutlet(v) or nil
                if outlet ~= nil then
                    local ox, oy, oz = getWorldTranslation(outlet.node)
                    local distance = MathUtil.vector3Length(x - ox, y - oy, z - oz)
                    if distance <= radius + 0.4 and (bestDistance == nil or distance < bestDistance) then
                        local nx, _, nz = localDirectionToWorld(outlet.node, -1, 0, 0)
                        nx, _, nz = L.normalize(nx, 0, nz)
                        best, bestDistance, bestPush = v, distance, false
                        bx, by, bz, bdx, bdz = ox, oy, oz, -nx, -nz
                    end
                end
            elseif getWaterUnit(v) ~= nil and hasDischargeNodes(v) then
                -- IBC / cisterna s vypouštěcím uzlem: hadice jde jen na výstup (uzel), ne kamkoli na karoserii
                local node, distance = findDischargeNode(v, x, y, z, radius + SprayDroneWaterHose.OUTLET_REACH)
                local box = node ~= nil and L.boxOf(v) or nil
                if node ~= nil and box ~= nil and (bestDistance == nil or distance < bestDistance) then
                    local ox, oy, oz = getWorldTranslation(node)
                    local nx, _, nz = L.normalize(x - ox, 0, z - oz)
                    if math.abs(nx) + math.abs(nz) < 1e-4 then
                        nx, _, nz = L.normalize(ox - box.x, 0, oz - box.z)
                    end
                    best, bestDistance, bestPush = v, distance, false
                    bx, by, bz, bdx, bdz = ox, oy, oz, -nx, -nz
                    local px, py, pz, pdx, pdz = findSurface(v, ox + nx * 1.5, oz + nz * 1.5, ox - nx * 1.2, oz - nz * 1.2,
                        { oy, oy + 0.1, oy - 0.1, oy + 0.25, oy - 0.25 })
                    if px ~= nil and MathUtil.vector3Length(px - ox, py - oy, pz - oz) <= SprayDroneWaterHose.OUTLET_SNAP then
                        bx, by, bz, bdx, bdz = px, py, pz, pdx, pdz
                    else
                        -- uzel je mimo karoserii (za nárazníkem): hadice na nejbližší povrch u uzlu, ne do vzduchu
                        local _, sx, sy, sz, sdx, sdz = snapToBody(v, ox + nx, oz + nz, 3)
                        if sx ~= nil then
                            bx, by, bz, bdx, bdz = sx, sy, sz, sdx, sdz
                        end
                    end
                end
            elseif getWaterUnit(v) ~= nil then
                local distance, sx, sy, sz, sdx, sdz = snapToBody(v, x, z, radius)
                if distance ~= nil and (bestDistance == nil or distance < bestDistance) then
                    best, bestDistance, bestPush = v, distance, false
                    bx, by, bz, bdx, bdz = sx, sy, sz, sdx, sdz
                end
            elseif canPush and getWaterSinkUnit(v) ~= nil then
                -- nádrž bez vody (prázdná cisterna, IBC): hadice vleku do ní vodu napouští
                local distance, sx, sy, sz, sdx, sdz = snapToBody(v, x, z, radius)
                if distance ~= nil and (bestDistance == nil or distance < bestDistance) then
                    best, bestDistance, bestPush = v, distance, true
                    bx, by, bz, bdx, bdz = sx, sy, sz, sdx, sdz
                end
            end
        end
    end
    return best, bx, by, bz, bdx, bdz, bestPush
end

-- Je u konce hadice cizí nádrž, která bere vodu, ale žádnou nemá? Pak se hadice nepřipojí jen proto, že není z čeho čerpat (hráči se to řekne).
local function isDryTankAt(self, x, y, z, radius)
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if v ~= self and not v.isDeleted and v.rootNode ~= nil and entityExists(v.rootNode) and v[SprayDronePump.SPEC_NAME] == nil
            and v.spec_fillUnit ~= nil and v.getFillUnitSupportsFillType ~= nil and getWaterUnit(v) == nil then
            for index = 1, #v.spec_fillUnit.fillUnits do
                if v:getFillUnitSupportsFillType(index, FillType.WATER) and v:getFillUnitCapacity(index) > 100 and snapToBody(v, x, z, radius) ~= nil then
                    return true
                end
            end
        end
    end
    return false
end

-- Je vodní ventil vozidla obsazený hadicí? Buď vlastní hadicí vleku (hose 1), nebo výstupní hadicí pumpy (kromě hadice ignore).
function SprayDroneWaterHose.isPortOccupied(vehicle, portIndex, ignore)
    local own = getSpec(vehicle).hoses[1]
    if own ~= nil and own.out and own.port == portIndex then
        return true
    end
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        local spec = v[SprayDroneWaterHose.SPEC_NAME]
        if spec ~= nil and not v.isDeleted then
            for _, h in ipairs(spec.hoses) do
                if h ~= ignore and h.out and not h.held and h.source == vehicle and h.targetPort == portIndex then
                    return true
                end
            end
        end
    end
    return false
end

-- Vodní ventil vleku nejblíž bodu (x, y, z) do vzdálenosti radius, na který jde připojit výstupní hadici pumpy: vozidlo, číslo ventilu a bod
-- připojení (čelo ventilu) s vodorovným směrem do vozidla; nil, když žádný ventil není dost blízko nebo je obsazený.
function SprayDroneWaterHose.findSinkAt(self, h, x, y, z, radius)
    local best, bestIndex, bestDistance, bx, by, bz, bdx, bdz
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if v ~= self and not v.isDeleted and v[SprayDroneWaterHose.SPEC_NAME] ~= nil and v[SprayDronePump.SPEC_NAME] == nil and v.rootNode ~= nil
            and entityExists(v.rootNode) and g_currentMission.accessHandler:canFarmAccess(self:getOwnerFarmId(), v) then
            for _, p in ipairs(SprayDroneWaterHose.getActivePorts(v, 1)) do
                if p.port.kind == "water" and not SprayDroneWaterHose.isPortOccupied(v, p.index, h) then
                    local px, py, pz = getWorldTranslation(p.node)
                    local distance = MathUtil.vector3Length(x - px, y - py, z - pz)
                    if distance <= radius and (bestDistance == nil or distance < bestDistance) then
                        local nx, _, nz = localDirectionToWorld(p.node, -1, 0, 0)
                        nx, _, nz = L.normalize(nx, 0, nz)
                        best, bestIndex, bestDistance = v, p.index, distance
                        bx, by, bz, bdx, bdz = px, py, pz, -nx, -nz
                    end
                end
            end
        end
    end
    if best ~= nil then
        return best, bestIndex, bx, by, bz, bdx, bdz
    end
    -- žádný ventil vleku: cisterna, IBC nebo postřikovač kamkoli na karoserii
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if v ~= self and not v.isDeleted and v.rootNode ~= nil and entityExists(v.rootNode) and getWaterSinkUnit(v) ~= nil
            and g_currentMission.accessHandler:canFarmAccess(self:getOwnerFarmId(), v) then
            local distance, sx, sy, sz, sdx, sdz = snapToBody(v, x, z, radius)
            if distance ~= nil and (bestDistance == nil or distance < bestDistance) then
                best, bestIndex, bestDistance = v, SprayDroneWaterHose.TANK_ARG, distance
                bx, by, bz, bdx, bdz = sx, sy, sz, sdx, sdz
            end
        end
    end
    return best, bestIndex, bx, by, bz, bdx, bdz
end

local pondProbe = {}

function pondProbe:callback(nodeId, x, y, z)
    if nodeId ~= nil and nodeId ~= 0 then
        self.y = y
    end
    return false
end

-- Je v bodě (x, z) voda aspoň minDepth hluboká (hladina nad terénem)? Vrací pravdu, hladinu a terén pod ní.
local function getPondDepth(x, z, minDepth)
    local ground = L.terrainAt(x, z)
    pondProbe.y = nil
    raycastClosest(x, ground + 40, z, 0, -1, 0, 80, "callback", pondProbe, CollisionFlag.WATER)
    if pondProbe.y == nil then
        return false, nil, ground
    end
    return pondProbe.y - ground >= minDepth, pondProbe.y, ground
end

-- Bod pro koš hadice pumpy u ruky (x, z): na dně pod vodou, jinak nil. Hráč stojí na břehu a ruka sahá jen ~0,85 m před něj, takže když pod rukou není dost
-- hluboko, hledá se nejbližší dost hluboká voda v okruhu POND_REACH kolem ruky (koš se hodí do vody).
function SprayDroneWaterHose.findPondAt(self, x, z)
    local pump = self[SprayDronePump.SPEC_NAME]
    local minDepth = pump ~= nil and pump.minDepth or SprayDroneWaterHose.POND_DEPTH
    for _, radius in ipairs({ 0, 0.5, 1.0, SprayDroneWaterHose.POND_REACH }) do
        for k = 0, radius == 0 and 0 or 7 do
            local a = k * math.pi / 4
            local px, pz = x + math.cos(a) * radius, z + math.sin(a) * radius
            local ok, _, ground = getPondDepth(px, pz, minDepth)
            if ok then
                return px, ground + 0.12, pz
            end
        end
    end
    return nil
end

---------------------------------------------------------------------------------------------------
-- příkazy (server)

local function setState(self, h, out, held)
    local spec = getSpec(self)
    h.out, h.held = out, held
    if not held then
        h.localHold = false
    end
    if not out then
        h.source = nil
        h.targetPort = nil
        h.pond = false
        h.warned = false
        h.valveOpen = false
    end
    self:raiseDirtyFlags(spec.dirtyFlag)
    self:raiseActive()
end

-- Záznam toku hadicí do log.txt (SDT děj): začátek přelévání zdroj -> cíl a po FLOW_QUIET_MS bez přelitého litru konec s množstvím.
SprayDroneWaterHose.FLOW_QUIET_MS = 800

local function flowName(v)
    return v ~= nil and string.format("%s (id %s)", v.configFileNameClean or "?", tostring(v.id)) or "rybník"
end

-- Záznam při pouštění hadice: co je v okolí konce hadice a proč se nepřipojila (vozidla do 6 m, jejich nádrže a vypouštěcí uzly).
local function describeSurroundings(self, h)
    local W = SprayDroneWaterHose
    local lines = {}
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if v ~= self and not v.isDeleted and v.rootNode ~= nil and entityExists(v.rootNode) and v.spec_fillUnit ~= nil then
            local vx, vy, vz = getWorldTranslation(v.rootNode)
            if MathUtil.vector3Length(h.holdX - vx, 0, h.holdZ - vz) <= 12 then
                local box = L.boxOf(v)
                local gap = "?"
                if box ~= nil then
                    local dx, dz = h.holdX - box.x, h.holdZ - box.z
                    local u, w = dx * box.ux + dz * box.uz, dx * box.wx + dz * box.wz
                    gap = string.format("%.2f", MathUtil.vector2Length(u - math.clamp(u, -box.hu, box.hu), w - math.clamp(w, -box.hw, box.hw)))
                end
                local units = {}
                for index = 1, #v.spec_fillUnit.fillUnits do
                    table.insert(units, string.format("%d:%s %.0f l%s", index, tostring(g_fillTypeManager:getFillTypeNameByIndex(v:getFillUnitFillType(index)) or "-"),
                        v:getFillUnitFillLevel(index), v:getFillUnitSupportsFillType(index, FillType.WATER) and " (bere vodu)" or ""))
                end
                local nodes = {}
                for _, dn in ipairs(getDischargeNodes(v) or {}) do
                    table.insert(nodes, string.format("%s", isLowNode(v, dn.node) and "nízký" or "vysoký"))
                end
                local ports = {}
                if v[SprayDroneWaterHose.SPEC_NAME] ~= nil then
                    for index, port in ipairs(W.getPorts(v, 1)) do
                        if entityExists(port.node) then
                            local px, py, pz = getWorldTranslation(port.node)
                            table.insert(ports, string.format("%d:%s %.2f m%s", index, port.kind, MathUtil.vector3Length(h.holdX - px, h.holdY - py, h.holdZ - pz),
                                isNodeVisible(port.node) and "" or " skrytý"))
                        end
                    end
                end
                table.insert(lines, string.format("%s (id %s) mezera od karoserie %s m, nádrže [%s], vypouštěcí uzly [%s], voda %s, ventily [%s]", v.configFileNameClean or "?", tostring(v.id), gap,
                    table.concat(units, "; "), table.concat(nodes, ","), tostring(getWaterUnit(v) ~= nil), table.concat(ports, "; ")))
            end
        end
    end
    local pump = self[SprayDronePump.SPEC_NAME]
    if pump ~= nil then
        local ok, level, ground = getPondDepth(h.holdX, h.holdZ, 0.01)
        table.insert(lines, string.format("pumpa: režim vstupu %s, voda pod koncem hadice %s (hladina %s, terén %.2f, nejmenší hloubka %.2f m)",
            pump.pondMode and "rybník" or "nádrž", tostring(ok), level ~= nil and string.format("%.2f", level) or "žádná", ground, pump.minDepth or SprayDroneWaterHose.POND_DEPTH))
    end
    if #lines > 0 then
        if SprayDroneDebug and SprayDroneDebug.ENABLED then
            Logging.info("SDT děj: hadice %d na %s pustena ve výšce %.2f m (%.1f %.1f), okolí: %s", h.index, flowName(self), h.holdY or 0, h.holdX, h.holdZ, table.concat(lines, " | "))
        end
    end
end

local function noteFlow(self, h, dst, src, moved)
    if moved > 0 then
        if not h.flowOn then
            h.flowOn, h.flowTotal, h.flowStart = true, 0, g_time
            if SprayDroneDebug and SprayDroneDebug.ENABLED then
                Logging.info("SDT děj: hadice %d na %s: tok začal, %s -> %s", h.index, flowName(self), flowName(src), flowName(dst))
            end
        end
        h.flowTotal = h.flowTotal + moved
        h.flowLast = g_time
    end
end

local function flushFlow(self, h, force)
    if h.flowOn and (force or g_time - h.flowLast >= SprayDroneWaterHose.FLOW_QUIET_MS) then
        h.flowOn = false
        if SprayDroneDebug and SprayDroneDebug.ENABLED then
            Logging.info("SDT děj: hadice %d na %s: tok skončil, přeteklo %.1f l za %.1f s", h.index, flowName(self), h.flowTotal, (h.flowLast - h.flowStart) / 1000)
        end
    end
end

function SprayDroneWaterHose.command(self, command, target, arg, noEventSend, x, y, z, dx, dy, dz, hoseIndex)
    if SprayDroneWaterHoseEvent.sendEvent(self, command, target, arg, noEventSend, x, y, z, dx, dy, dz, hoseIndex) then
        return
    end
    local spec = getSpec(self)
    local h = spec.hoses[hoseIndex or 1]
    if h == nil then
        return
    end
    local W = SprayDroneWaterHose
    if command ~= W.CMD_DRAG then
        local names = { [W.CMD_TAKE] = "vzetí", [W.CMD_DROP] = "odložení", [W.CMD_CONNECT] = "připojení ke zdroji" }
        local detail = ""
        if command == W.CMD_CONNECT then
            detail = " " .. (target ~= nil and flowName(target) or (arg == W.POND_ARG and "voda rybníka" or "?"))
        end
        SprayDroneSound.noteAction(string.format("hadice %d na %s: %s%s (port %s)", h.index, self.configFileNameClean or "?", names[command] or tostring(command),
            detail, tostring(h.port)))
    end
    if command == W.CMD_DROP then
        flushFlow(self, h, true)
        if h.held and h.holdX ~= nil then
            describeSurroundings(self, h)
        end
    end
    if command == W.CMD_TAKE then
        if not h.out and x ~= nil then
            h.port = math.clamp(arg or 1, 1, 15)
            h.holdX, h.holdY, h.holdZ = x, y, z
            h.holdDX, h.holdDY, h.holdDZ = dx or 0, dy or 0, dz or 1
            setState(self, h, true, true)
        end
    elseif command == W.CMD_DRAG then
        if h.held and x ~= nil then
            h.holdX, h.holdY, h.holdZ = x, y, z
            h.holdDX, h.holdDY, h.holdDZ = dx or 0, dy or 0, dz or 1
            self:raiseDirtyFlags(spec.dirtyFlag)
        end
    elseif command == W.CMD_DROP then
        setState(self, h, false, false)
    elseif command == W.CMD_CONNECT then
        if h.out and h.held and x ~= nil then
            if arg == W.POND_ARG then
                local px, py, pz = W.findPondAt(self, x, z)
                if px ~= nil then
                    h.srcX, h.srcY, h.srcZ = px, py, pz
                    local nx, _, nz = L.normalize(dx or 0, 0, dz or 1)
                    h.srcDX, h.srcDZ = nx, nz
                    h.pond = true
                    h.source = nil
                    h.valveOpen = false
                    setState(self, h, true, false)
                end
            elseif target ~= nil and not target.isDeleted then
                h.srcX, h.srcY, h.srcZ = worldToLocal(target.rootNode, x, y, z)
                local ldx, _, ldz = worldDirectionToLocal(target.rootNode, dx, 0, dz)
                h.srcDX, _, h.srcDZ = L.normalize(ldx, 0, ldz)
                h.source = target
                h.targetPort = arg ~= nil and arg > 0 and arg or nil
                target.sdtSoundWatch = true
                h.valveOpen = true
                setState(self, h, true, false)
            end
        end
    end
end

---------------------------------------------------------------------------------------------------
-- chod (server): čerpání, utržení, obnovení po načtení hry

-- Bod připojení hadice na zdroji ve světě: x, y, z a vodorovný směr do zdroje dx, dz (nil, když zdroj zmizel). U rybníka světový bod koše.
function SprayDroneWaterHose.getAttachWorld(self, h)
    h = h or getSpec(self).hoses[1]
    if h.pond then
        return h.srcX, h.srcY, h.srcZ, h.srcDX, h.srcDZ
    end
    local source = h.source
    if source == nil or source.isDeleted or source.rootNode == nil or not entityExists(source.rootNode) then
        return nil
    end
    local x, y, z = localToWorld(source.rootNode, h.srcX, h.srcY, h.srcZ)
    local dx, _, dz = localDirectionToWorld(source.rootNode, h.srcDX, 0, h.srcDZ)
    dx, _, dz = L.normalize(dx, 0, dz)
    return x, y, z, dx, dz
end

local function notify(key)
    if g_currentMission ~= nil and g_currentMission.showBlinkingWarning ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText(key), 3000)
    end
end

local function resolvePending(self, h, dt)
    local spec = getSpec(self)
    h.pendingTime = h.pendingTime - dt
    local port = SprayDroneWaterHose.getPorts(self, h.index)[h.pendingPort]
    if port == nil or h.pendingPond ~= (port.kind == "pond") then
        h.pendingId, h.pendingPond = nil, false
        return
    end
    if h.pendingPond then
        h.pendingPond = false
        h.pendingId = nil
        h.srcX, h.srcY, h.srcZ = unpack(h.pendingPos)
        h.srcDX, h.srcDZ = unpack(h.pendingDir)
        h.pond = true
        h.port = h.pendingPort
        setState(self, h, true, false)
        return
    end
    local vehicles = g_currentMission.vehicleSystem ~= nil and g_currentMission.vehicleSystem.vehicles or {}
    for _, v in ipairs(vehicles) do
        if v ~= self and not v.isDeleted and v.getUniqueId ~= nil and v:getUniqueId() == h.pendingId then
            h.source = v
            v.sdtSoundWatch = true
            h.port = h.pendingPort
            h.targetPort = h.pendingTarget
            h.srcX, h.srcY, h.srcZ = unpack(h.pendingPos)
            h.srcDX, h.srcDZ = unpack(h.pendingDir)
            h.pendingId = nil
            setState(self, h, true, false)
            h.valveOpen = true
            return
        end
    end
    if h.pendingTime <= 0 then
        h.pendingId = nil
    end
end

-- Přelije z nádrže zdroje do nádrže cíle (dst, dstUnit); vrací, kolik se přelilo.
local function transfer(h, dst, dstUnit, dstType, src, srcUnit, srcType, maxRate, seconds)
    local level = dst:getFillUnitFillLevel(dstUnit)
    if level > SprayDroneWaterHose.MIN_LITERS and dst:getFillUnitFillType(dstUnit) ~= dstType then
        if not h.warned then
            h.warned = true
            notify("sdt_wh_mixed")
        end
        return 0
    end
    local amount = math.min(maxRate * seconds, src:getFillUnitFillLevel(srcUnit), dst:getFillUnitFreeCapacity(dstUnit))
    if amount <= SprayDroneWaterHose.MIN_LITERS then
        return 0
    end
    local before = dst:getFillUnitFillLevel(dstUnit)
    dst:addFillUnitFillLevel(dst:getOwnerFarmId(), dstUnit, amount, dstType, ToolType.UNDEFINED, nil)
    local moved = dst:getFillUnitFillLevel(dstUnit) - before
    if moved > 0 then
        src:addFillUnitFillLevel(src:getOwnerFarmId(), srcUnit, -moved, srcType, ToolType.UNDEFINED, nil)
    end
    return math.max(moved, 0)
end

function SprayDroneWaterHose.updateServer(self, h, dt)
    local spec = getSpec(self)
    flushFlow(self, h, not h.out)
    if h.pendingId ~= nil or h.pendingPond then
        self:raiseActive()
        resolvePending(self, h, dt)
    end
    if not h.out then
        return
    end
    self:raiseActive()
    local port = SprayDroneWaterHose.getPorts(self, h.index)[h.port]
    if port == nil or not entityExists(port.node) then
        return
    end
    local px, py, pz = getWorldTranslation(port.node)
    if h.held then
        if MathUtil.vector3Length(h.holdX - px, h.holdY - py, h.holdZ - pz) > h.hoseLength + 2 then
            SprayDroneSound.noteAction("hadice utržena při nesení (příliš daleko)")
            setState(self, h, false, false)
            notify("sdt_wh_torn")
        end
        return
    end
    local ax, ay, az = SprayDroneWaterHose.getAttachWorld(self, h)
    if ax == nil or MathUtil.vector3Length(ax - px, ay - py, az - pz) > h.hoseLength then
        local hadSource = h.source ~= nil or h.pond
        SprayDroneSound.noteAction("hadice utržena nebo ztratila zdroj")
        setState(self, h, false, false)
        if hadSource then
            notify("sdt_wh_torn")
        end
        return
    end
    local pump = self[SprayDronePump.SPEC_NAME]
    local running = pump == nil or SprayDronePump.isRunning(self)
    local seconds = dt * 0.001
    if port.kind == "water" and h.targetPort == SprayDroneWaterHose.TANK_ARG then
        -- hadice vleku do cizí nádrže bez vody (cisterna, IBC): voda teče z nádrže vleku do ní
        local source = h.source
        local unit = getWaterSinkUnit(source)
        local own = getWaterUnit(self)
        if unit ~= nil and own ~= nil and running and self:getFillUnitExists(port.fillUnitIndex) then
            local moved = transfer(h, source, unit, FillType.WATER, self, port.fillUnitIndex, FillType.WATER, h.rate, seconds)
            noteFlow(self, h, source, self, moved)
        end
    elseif port.kind == "water" then
        local source = h.source
        local unit = getWaterUnit(source)
        if unit ~= nil and running and self:getFillUnitExists(port.fillUnitIndex) then
            local moved = transfer(h, self, port.fillUnitIndex, port.fillType, source, unit, FillType.WATER, h.rate, seconds)
            noteFlow(self, h, self, source, moved)
            if moved > 0 and pump ~= nil then
                SprayDronePump.markFlow(self)
            end
        end
    elseif port.kind == "pond" then
        h.pondTimer = h.pondTimer - dt
        if h.pondTimer <= 0 then
            h.pondTimer = SprayDroneWaterHose.POND_CHECK_MS
            h.inWater = getPondDepth(h.srcX, h.srcZ, pump ~= nil and pump.minDepth or SprayDroneWaterHose.POND_DEPTH)
        end
        if h.inWater and running then
            local amount = math.min(h.rate * seconds, self:getFillUnitFreeCapacity(port.fillUnitIndex))
            if amount > SprayDroneWaterHose.MIN_LITERS then
                self:addFillUnitFillLevel(self:getOwnerFarmId(), port.fillUnitIndex, amount, FillType.WATER, ToolType.UNDEFINED, nil)
                noteFlow(self, h, self, nil, amount)
                SprayDronePump.markFlow(self)
            end
        end
    elseif port.kind == "sink" then
        local target = h.source
        if target ~= nil and h.targetPort == SprayDroneWaterHose.TANK_ARG then
            local unit = running and getWaterSinkUnit(target) or nil
            if unit ~= nil then
                local moved = transfer(h, target, unit, FillType.WATER, self, port.fillUnitIndex, FillType.WATER, h.rate, seconds)
                noteFlow(self, h, target, self, moved)
                if moved > 0 then
                    SprayDronePump.markFlow(self)
                end
            end
            return
        end
        local tport = target ~= nil and h.targetPort ~= nil and SprayDroneWaterHose.getPorts(target, 1)[h.targetPort] or nil
        if tport ~= nil and running and target:getFillUnitExists(tport.fillUnitIndex) then
            local moved = transfer(h, target, tport.fillUnitIndex, tport.fillType, self, port.fillUnitIndex, FillType.WATER, h.rate, seconds)
            noteFlow(self, h, target, self, moved)
            if moved > 0 then
                SprayDronePump.markFlow(self)
            end
        end
    else
        local source = h.source
        local module = getLimeModule(source)
        local outlet = module ~= nil and module.getOutlet(source) or nil
        if outlet ~= nil and not outlet.closed and module.isRunning(source) and h.valveOpen and self:getFillUnitExists(port.fillUnitIndex) then
            local moved = transfer(h, self, port.fillUnitIndex, port.fillType, source, outlet.fillUnitIndex, outlet.fillType, math.min(h.rate, outlet.rate),
                seconds)
            noteFlow(self, h, self, source, moved)
            if moved > 0 then
                module.markPumping(source)
            end
        end
    end
end

---------------------------------------------------------------------------------------------------
-- vykreslení (klient i server)

function SprayDroneWaterHose.showChain(h, shown)
    for _, node in ipairs(h.segments) do
        setVisibility(node, shown)
    end
    if h.storzEnd ~= nil then
        setVisibility(h.storzEnd, shown and h.hoseEnd == h.storzEnd)
    end
    if h.strainerEnd ~= nil then
        setVisibility(h.strainerEnd, shown and h.hoseEnd == h.strainerEnd)
    end
    h.shown = shown
end

-- Koncovka hadice vstupu pumpy podle režimu: spojka Storz (nádrž) nebo sací koš (rybník); hoseEnd je ta, kterou SprayDroneHoseLib.layoutChain polohuje.
local function selectEnd(self, h)
    if h.strainerEnd == nil then
        return
    end
    local pump = self[SprayDronePump.SPEC_NAME]
    local want = (pump ~= nil and pump.pondMode) and h.strainerEnd or h.storzEnd
    if want ~= h.hoseEnd then
        h.hoseEnd = want
        SprayDroneWaterHose.showChain(h, h.shown)
    end
end

local function getPlayerPosition()
    local player = g_localPlayer
    if player == nil then
        return nil
    end
    local vehicle = player.getCurrentVehicle ~= nil and player:getCurrentVehicle() or nil
    if vehicle ~= nil or player.getPosition == nil then
        return nil
    end
    return player:getPosition()
end

-- Články, které se nemají kam položit (zdroj ještě není načtený nebo zmizel), by zůstaly nakupené v počátku vleku na zemi.
local function hideUnplaced(h)
    h.unplaced = true
    if h.shown then
        SprayDroneWaterHose.showChain(h, false)
    end
end

function SprayDroneWaterHose.layout(self, h)
    local port = SprayDroneWaterHose.getPorts(self, h.index)[h.port]
    if port == nil or not entityExists(port.node) then
        hideUnplaced(h)
        return
    end
    local sx, sy, sz = getWorldTranslation(port.node)
    local hx, _, hz = localDirectionToWorld(port.node, -1, 0, 0)
    hx, _, hz = L.normalize(hx, 0, hz)
    local curve, edx, edy, edz
    if h.held then
        local fx, _, fz = L.normalize(-h.holdDX, 0, -h.holdDZ)
        if math.abs(h.holdDX) + math.abs(h.holdDZ) < 0.05 then
            fx, _, fz = L.normalize(sx - h.holdX, 0, sz - h.holdZ)
        end
        curve = L.hoseCurve(h, self, nil, h.hoseLength, { sx, sy, sz }, { hx, hz }, { h.holdX, h.holdY, h.holdZ }, { fx, fz })
        edx, edy, edz = -h.holdDX, -h.holdDY, -h.holdDZ
    else
        local ax, ay, az, adx, adz = SprayDroneWaterHose.getAttachWorld(self, h)
        if ax == nil then
            hideUnplaced(h)
            return
        end
        curve = L.hoseCurve(h, self, h.source, h.hoseLength, { sx, sy, sz }, { hx, hz }, { ax, ay, az }, { -adx, -adz })
        edx, edy, edz = -adx, 0, -adz
        local module = h.source ~= nil and getLimeModule(h.source) or nil
        if module ~= nil then
            module.markOutletUsed(h.source)
        end
    end
    L.layoutChain(h, curve, edx, edy, edz)
    if h.unplaced then
        h.unplaced = false
        SprayDroneWaterHose.showChain(h, true)
    end
end

-- Páka kohoutu vstupu na koncentrát: otočená podle h.valveOpen (stav jde ze serveru, takže ji vidí každý klient).
function SprayDroneWaterHose.updateValve(self, h, dt)
    local port = h.out and h.source ~= nil and SprayDroneWaterHose.getPorts(self, h.index)[h.port] or nil
    local lime = SprayDroneStation.getLimeInlet(self)
    local node = lime ~= nil and lime.valveNode or nil
    if h.index ~= 1 or node == nil or not entityExists(node) then
        return
    end
    local goal = (port ~= nil and port.kind == "lime" and h.valveOpen) and 1 or 0
    if h.valveAnim ~= goal then
        local step = dt * 0.001 / SprayDroneWaterHose.VALVE_TIME
        if goal > h.valveAnim then
            h.valveAnim = math.min(h.valveAnim + step, goal)
        else
            h.valveAnim = math.max(h.valveAnim - step, goal)
        end
        local t = h.valveAnim * h.valveAnim * (3 - 2 * h.valveAnim)
        setRotation(node, 0, math.rad(lime.valveOpenAngle) * t, 0)
        self:raiseActive()
    end
end

function SprayDroneWaterHose:onUpdate(dt)
    local spec = getSpec(self)
    for _, h in ipairs(spec.hoses) do
        if self.isServer then
            SprayDroneWaterHose.updateServer(self, h, dt)
        end
        SprayDroneWaterHose.updateValve(self, h, dt)
        selectEnd(self, h)
        if not h.out then
            h.unplaced = false
        end
        if h.out ~= h.shown and not (h.out and h.unplaced) then
            SprayDroneWaterHose.showChain(h, h.out)
        end
        if h.out then
            if self.isClient and h.localHold then
                if getPlayerPosition() == nil then
                    self:sprayDroneWaterHoseCommand(SprayDroneWaterHose.CMD_DROP, nil, nil, nil, nil, nil, nil, nil, nil, nil, h.index)
                    h.localHold = false
                else
                    local port = SprayDroneWaterHose.getPorts(self, h.index)[h.port]
                    local x, y, z, dx, dy, dz = L.getHandPosition(h, port ~= nil and port.node or nil, h.hoseLength)
                    if x ~= nil then
                        h.holdX, h.holdY, h.holdZ, h.holdDX, h.holdDY, h.holdDZ = x, y, z, dx, dy, dz
                        h.dragTimer = h.dragTimer - dt
                        if h.dragTimer <= 0 then
                            h.dragTimer = SprayDroneWaterHose.DRAG_INTERVAL
                            self:sprayDroneWaterHoseCommand(SprayDroneWaterHose.CMD_DRAG, nil, 0, nil, x, y, z, dx, dy, dz, h.index)
                        end
                    end
                end
            end
            SprayDroneWaterHose.layout(self, h)
            self:raiseActive()
        end
    end
end

---------------------------------------------------------------------------------------------------
-- ovládání: R u spojky / u konce hadice, levé tlačítko myši u vstupu na koncentrát = kohout, u vstupní spojky pumpy = přepnutí režimu vstupu

local function isUsable(vehicle)
    if vehicle == nil or vehicle.isDeleted or g_localPlayer == nil then
        return false
    end
    if VehiclePropertyState ~= nil and vehicle.propertyState == VehiclePropertyState.SHOP_CONFIG then
        return false
    end
    return g_currentMission.accessHandler:canFarmAccess(g_localPlayer.farmId, vehicle)
end

SprayDroneWaterHoseActivatable = {}
local SprayDroneWaterHoseActivatable_mt = Class(SprayDroneWaterHoseActivatable)

function SprayDroneWaterHoseActivatable.new(vehicle)
    local self = setmetatable({}, SprayDroneWaterHoseActivatable_mt)
    self.vehicle = vehicle
    self.activateText = g_i18n:getText("sdt_wh_take")
    self.distance = 0
    return self
end

local TAKE_TEXTS = { lime = "sdt_wh_takeLime", pond = "sdt_wh_takePond", sink = "sdt_wh_takeOut" }

-- Co hráč s hadicí h právě může: "take" (u spojky vzít hadici), "hold" (nese konec: připojit, nebo pustit), "unplug" (u spojky nebo u druhého
-- konce odpojit; u vstupu na koncentrát navíc kohout). Vrací stav, klíč textu, vzdálenost pro výběr aktivátoru, cíl (zdroj, vlek s ventilem) a
-- údaje o bodu připojení (nebo číslo spojky u "take").
local function evaluateHose(vehicle, h, px, py, pz)
    local W = SprayDroneWaterHose
    local ports = W.getPorts(vehicle, h.index)
    local pump = vehicle[SprayDronePump.SPEC_NAME] ~= nil
    if h.localHold and h.held then
        local port = ports[h.port]
        local kind = port ~= nil and port.kind or "water"
        if kind == "pond" then
            local wx, wy, wz = W.findPondAt(vehicle, h.holdX, h.holdZ)
            return "hold", wx ~= nil and "sdt_wh_connectPond" or "sdt_wh_drop", 0, nil, wx ~= nil and { wx, wy, wz, h.holdDX, h.holdDZ, W.POND_ARG } or nil
        elseif kind == "sink" then
            local target, tIndex, bx, by, bz, bdx, bdz = W.findSinkAt(vehicle, h, h.holdX, h.holdY, h.holdZ, W.SINK_RADIUS)
            local text = target == nil and "sdt_wh_drop" or (tIndex == W.TANK_ARG and "sdt_wh_connectTank" or "sdt_wh_connectTrailer")
            return "hold", text, 0, target, { bx, by, bz, bdx, bdz, tIndex }
        end
        local source, bx, by, bz, bdx, bdz, push = W.findSourceAt(vehicle, h.holdX, h.holdY, h.holdZ, W.SOURCE_RADIUS, kind)
        local text = source ~= nil and (push and "sdt_wh_connectTank" or "sdt_wh_connect")
            or (kind == "water" and isDryTankAt(vehicle, h.holdX, h.holdY, h.holdZ, W.SOURCE_RADIUS) and "sdt_wh_tankEmpty" or "sdt_wh_drop")
        return "hold", text, 0, source, { bx, by, bz, bdx, bdz, push and W.TANK_ARG or nil }
    end
    if h.out then
        if h.held then
            return nil
        end
        local port = ports[h.port]
        if port ~= nil and entityExists(port.node) then
            local nx, ny, nz = getWorldTranslation(port.node)
            local d = MathUtil.vector3Length(px - nx, py - ny, pz - nz)
            if d <= W.PORT_DISTANCE then
                return "unplug", "sdt_wh_unplug", SprayDroneLink.aimDistance(d, port.node), nil, port.kind
            end
        end
        local ax, ay, az = W.getAttachWorld(vehicle, h)
        if ax ~= nil then
            local d = MathUtil.vector3Length(px - ax, py - ay, pz - az)
            if d <= W.UNPLUG_DISTANCE then
                return "unplug", "sdt_wh_unplug", d
            end
        end
        return nil
    end
    local best, bestDistance
    for _, p in ipairs(W.getActivePorts(vehicle, h.index)) do
        local nx, ny, nz = getWorldTranslation(p.node)
        local d = MathUtil.vector3Length(px - nx, py + 1.0 - ny, pz - nz)
        if d <= W.PORT_DISTANCE and (bestDistance == nil or d < bestDistance) and not (h.index == 1 and not pump and W.isPortOccupied(vehicle, p.index, h)) then
            best, bestDistance = p, d
        end
    end
    if best ~= nil then
        local text = TAKE_TEXTS[best.port.kind] or (pump and "sdt_wh_takeIn" or "sdt_wh_take")
        return "take", text, SprayDroneLink.aimDistance(bestDistance, best.node), nil, best.index
    end
    return nil
end

-- Nejbližší použitelná hadice vozidla (nesená má přednost): stav, text, vzdálenost, cíl, údaje a číslo hadice.
local function evaluate(vehicle)
    local px, py, pz = getPlayerPosition()
    if px == nil or not isUsable(vehicle) then
        return nil
    end
    local best
    for _, h in ipairs(getSpec(vehicle).hoses) do
        local state, textKey, distance, source, extra = evaluateHose(vehicle, h, px, py, pz)
        if state ~= nil then
            if state == "hold" then
                return state, textKey, distance, source, extra, h.index
            end
            if best == nil or distance < best[3] then
                best = { state, textKey, distance, source, extra, h.index }
            end
        end
    end
    if best ~= nil then
        return unpack(best)
    end
    return nil
end

function SprayDroneWaterHoseActivatable:getIsActivatable()
    local state, textKey, distance, source, extra, hoseIndex = evaluate(self.vehicle)
    self.state, self.distanceTo, self.source, self.extra, self.hoseIndex = state, distance, source, extra, hoseIndex
    if state == nil then
        return false
    end
    self.activateText = g_i18n:getText(textKey)
    if self.eventId ~= nil then
        g_inputBinding:setActionEventText(self.eventId, self.activateText)
    end
    if self.clickEventId ~= nil then
        local mode = SprayDroneWaterHoseActivatable.isModePort(self.vehicle, state, extra, hoseIndex)
        g_inputBinding:setActionEventTextVisibility(self.clickEventId, mode and SprayDroneLink.mayClick(self))
        if mode then
            g_inputBinding:setActionEventText(self.clickEventId, SprayDronePump.getModeText(self.vehicle))
        end
    end
    return true
end

-- Hráč stojí u vstupní spojky pumpy (hadice odložená nebo připojená u spojky): levé tlačítko myši tam přepíná režim vstupu, ne bere hadici.
function SprayDroneWaterHoseActivatable.isModePort(vehicle, state, extra, hoseIndex)
    local port
    if state == "take" then
        port = SprayDroneWaterHose.getPorts(vehicle, hoseIndex)[extra]
    elseif state == "unplug" and extra ~= nil then
        port = SprayDroneWaterHose.getPorts(vehicle, hoseIndex)[getSpec(vehicle).hoses[hoseIndex].port]
    end
    return port ~= nil and port.inlet
end

function SprayDroneWaterHoseActivatable:getDistance(x, y, z)
    return self.distanceTo or 0
end

function SprayDroneWaterHoseActivatable:registerCustomInput(inputContext)
    local _, eventId = g_inputBinding:registerActionEvent(InputAction.ACTIVATE_OBJECT, self, self.run, false, true, false, true)
    g_inputBinding:setActionEventTextPriority(eventId, GS_PRIO_VERY_HIGH)
    g_inputBinding:setActionEventTextVisibility(eventId, true)
    g_inputBinding:setActionEventText(eventId, self.activateText)
    self.eventId = eventId
    -- levé tlačítko (ACTIVATE_HANDTOOL) jen u vstupní spojky pumpy přepíná režim vstupu; text se ukáže jen tam
    self.clickEventId = SprayDroneLink.registerClick(self, self.onClick, nil)
    SprayDroneLink.setSelected(self, true)
end

function SprayDroneWaterHoseActivatable:onClick()
    -- hadici se bere, připojuje a odpojuje jen klávesou R (run)
    if SprayDroneWaterHoseActivatable.isModePort(self.vehicle, self.state, self.extra, self.hoseIndex) and SprayDroneLink.mayClick(self) then
        SprayDronePump.toggleMode(self.vehicle)
    end
end

function SprayDroneWaterHoseActivatable:removeCustomInput(inputContext)
    g_inputBinding:removeActionEventsByTarget(self)
    SprayDroneLink.setSelected(self, false)
    self.eventId = nil
    self.clickEventId = nil
end

function SprayDroneWaterHoseActivatable:run()
    local vehicle = self.vehicle
    local h = getSpec(vehicle).hoses[self.hoseIndex or 1]
    local W = SprayDroneWaterHose
    local state = self.state
    if state == "take" then
        local port = W.getPorts(vehicle, h.index)[self.extra]
        h.port = self.extra
        local x, y, z, dx, dy, dz = L.getHandPosition(h, port.node, h.hoseLength)
        if x ~= nil then
            h.localHold = true
            h.holdX, h.holdY, h.holdZ, h.holdDX, h.holdDY, h.holdDZ = x, y, z, dx, dy, dz
            h.dragTimer = 0
            vehicle:sprayDroneWaterHoseCommand(W.CMD_TAKE, nil, self.extra, nil, x, y, z, dx, dy, dz, h.index)
        end
    elseif state == "hold" then
        h.localHold = false
        local p = self.extra
        local port = W.getPorts(vehicle, h.index)[h.port]
        if port ~= nil and port.kind == "pond" and p ~= nil then
            vehicle:sprayDroneWaterHoseCommand(W.CMD_CONNECT, nil, W.POND_ARG, nil, p[1], p[2], p[3], p[4], 0, p[5], h.index)
        elseif port ~= nil and port.kind == "sink" and self.source ~= nil then
            vehicle:sprayDroneWaterHoseCommand(W.CMD_CONNECT, self.source, p[6], nil, p[1], p[2], p[3], p[4], 0, p[5], h.index)
        elseif self.source ~= nil then
            vehicle:sprayDroneWaterHoseCommand(W.CMD_CONNECT, self.source, p[6] or 0, nil, p[1], p[2], p[3], p[4], 0, p[5], h.index)
        else
            vehicle:sprayDroneWaterHoseCommand(W.CMD_DROP, nil, nil, nil, nil, nil, nil, nil, nil, nil, h.index)
        end
    elseif state == "unplug" then
        vehicle:sprayDroneWaterHoseCommand(W.CMD_DROP, nil, nil, nil, nil, nil, nil, nil, nil, nil, h.index)
    end
end

function SprayDroneWaterHoseActivatable:activate() end

function SprayDroneWaterHoseActivatable:deactivate() end

function SprayDroneWaterHoseActivatable:draw() end
