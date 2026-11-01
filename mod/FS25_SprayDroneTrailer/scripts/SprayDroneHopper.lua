-- Přenosná násypka na jemně mleté vápno (objects/hopper/limeHopper.xml, vehicle type sdtLimeHopper = pallet + SprayDronePump + tahle specializace): lievec
-- s nástavcem (drobná zásoba, fill unit 2, SDT_FINE_LIME) a vlastní naftový motor (fill unit 1; motor, nafta, ovládání B a zvuk řeší SprayDronePump). Vápno se
-- do zásoby dostane dvěma cestami, obě bez motoru: pytel jemného vápna (limeBag50) naklopený víčkem dolů nad ústím se vysype (SprayDroneMill.updatePour
-- s druhem SDT_FINE_LIME) a vanilla big bag (limeBigBag) se nakladačem položí na výsypnou stolici nahoře (rám s náběhy, mřížkou a nožem) a sám sype
-- (Dischargeable vaku, canStartDischargeAutomatically) do exactFillRootNode pod mřížkou. Hladinu ukazuje vanilla fillPlane fill unitu 2.
--
-- Vysouvací opěry do kříže (<legs>): rameno se vysouvá šikmo z rohu rámu po své ose x, pak vizuální patka klesne na zem. Kolize patky (leg#collision)
-- stojí v i3d pevně ve vysunuté poloze, 1 cm pod spodkem rámu, a za běhu se nikdy neposouvá (posun compoundChild tvarů se tluče s přepnutím těla na
-- kinematické při upnutí na vlek, viz SprayDroneRelay.updateFreeze); jen se jí zapne filtr kolizí z i3d, když jsou opěry celé venku, a vypne (0, 0),
-- jakmile se začnou zasouvat. Vysunutá násypka tak stojí na čtyřech patkách (o 1 cm výš), zasunutou nese rám. Plný vak nahoře na lehké násypce se
-- snadno převrátí, proto vak sype jen s vysunutými opěrami
-- (getFillUnitSupportsToolType odmítne nástroj DISCHARGEABLE, dokud opěry nejsou celé venku); pytle jdou vždy. Opěry se vysouvají před položením vaku:
-- s vakem na stolici (findStoolBag) nejdou vysunout ani zasunout a hráč u násypky vidí, že vak se zasunutými opěrami nesype. Opěry vysouvá a zasouvá levé tlačítko myši u kterékoli patky (pěšky);
-- stav (legsOut) rozhoduje server a jde klientům ve stavu vozidla, pohyb nohou si každý počítá sám. Ven vápno táhne hadice velkého vleku z vápnové spojky
-- (kind lime) jako z výstupu mlýnku (SprayDroneWaterHose.getLimeModule): jen za chodu motoru, jen když v zásobě vápno je a v nádobce vleku je místo.

source(g_currentModDirectory .. "scripts/events/SprayDroneHopperEvent.lua")

SprayDroneHopper = {}
SprayDroneHopper.MOD_NAME = g_currentModName
SprayDroneHopper.MOD_DIR = g_currentModDirectory
SprayDroneHopper.SPEC_NAME = string.format("spec_%s.sprayDroneHopper", g_currentModName)

SprayDroneHopper.CMD_LEGS_OUT = 1
SprayDroneHopper.CMD_LEGS_IN = 2
SprayDroneHopper.CMD_BITS = 2
SprayDroneHopper.LEGS_DISTANCE = 1.8       -- hráč nejvýš tak daleko od patky opěry, aby opěry ovládal (m)
SprayDroneHopper.LEGS_SLIDE = 0.7          -- část pohybu opěr, kdy se rameno vysouvá; zbytek patka klesá k zemi
SprayDroneHopper.BAG_CHECK_MS = 500        -- jak často klient hledá vak na stolici kvůli nápovědě
SprayDroneHopper.HINT_DISTANCE = 6         -- do této vzdálenosti od násypky se ukazuje nápověda o zasunutých opěrách (m)

local function getSpec(self)
    return self[SprayDroneHopper.SPEC_NAME]
end

-- Potisk big bagu jemného vápna (objects/limeBigBag): vanilla vak nemá pojmenované sloty materiálů, takže fillTypeMaterials#materialSlotName
-- nic nenajde. Vak si vzhled podle druhu kopíruje z uzlu lime_mat (refNode), proto se po načtení vymění difuzní textura jeho materiálu.
SprayDroneHopper.BIG_BAG_FILE = "limebigbag.xml"
SprayDroneHopper.BIG_BAG_DIFFUSE = "objects/limeBigBag/textures/limebigbag_diffuse.dds"

function SprayDroneHopper.applyBigBagLabel(self)
    local name = self.configFileName
    if type(name) ~= "string" or string.sub(string.lower(name), -#SprayDroneHopper.BIG_BAG_FILE) ~= SprayDroneHopper.BIG_BAG_FILE then
        return
    end
    local node = I3DUtil.indexToObject(self.components, "lime_mat", self.i3dMappings)
    if node == nil then
        Logging.warning("SprayDroneHopper: big bag bez uzlu lime_mat, potisk jemného vápna se nepoužije")
        return
    end
    local material = setMaterialDiffuseMapFromFile(getMaterial(node, 0), SprayDroneHopper.MOD_DIR .. SprayDroneHopper.BIG_BAG_DIFFUSE, true, true, false)
    setMaterial(node, material, 0)
    for _, fillUnit in ipairs(self.spec_fillUnit ~= nil and self.spec_fillUnit.fillUnits or {}) do
        if fillUnit.fillTypeMaterials ~= nil then
            self:updateFillTypeMaterials(fillUnit.fillTypeMaterials, fillUnit.lastValidFillType or fillUnit.fillType)
        end
    end
end

if not SprayDroneHopper.bigBagHooked then
    SprayDroneHopper.bigBagHooked = true
    FillUnit.onLoad = Utils.appendedFunction(FillUnit.onLoad, SprayDroneHopper.applyBigBagLabel)
end

function SprayDroneHopper.prerequisitesPresent(specializations)
    return SpecializationUtil.hasSpecialization(FillUnit, specializations) and SpecializationUtil.hasSpecialization(SprayDronePump, specializations)
end

function SprayDroneHopper.initSpecialization()
    local schema = Vehicle.xmlSchema
    schema:setXMLSpecializationType("SprayDroneHopper")
    local key = "vehicle.sprayDroneHopper"
    schema:register(XMLValueType.INT, key .. "#limeFillUnitIndex", "Fill unit s jemným vápnem v lievci", 2)
    schema:register(XMLValueType.STRING, key .. "#fineFillType", "Druh jemného vápna", "SDT_FINE_LIME")
    schema:register(XMLValueType.FLOAT, key .. "#hoseRate", "Nejvyšší průtok výstupem jemného vápna (l/s)", 8)
    schema:register(XMLValueType.FLOAT, key .. "#pourRadius", "Víčko pytle nejvýš tak daleko od středu ústí lievce (m)", 0.5)
    schema:register(XMLValueType.FLOAT, key .. "#pourRate", "Sypání z pytle (l/s)", 8)
    schema:register(XMLValueType.NODE_INDEX, key .. ".nodes#funnel", "Střed ústí lievce")
    schema:register(XMLValueType.NODE_INDEX, key .. ".nodes#outlet", "Výstup jemného vápna (čelo spojky, sem se napojí hadice vleku)")
    schema:register(XMLValueType.FLOAT, key .. ".legs#travel", "O kolik se rameno opěry vysune ven po své ose x (m)", 0.30)
    schema:register(XMLValueType.FLOAT, key .. ".legs#drop", "O kolik patka po vysunutí klesne k zemi (m)", 0.05)
    schema:register(XMLValueType.FLOAT, key .. ".legs#duration", "Doba vysunutí opěr (s)", 2)
    schema:register(XMLValueType.NODE_INDEX, key .. ".legs.leg(?)#node", "Rameno opěry (posun po své ose x, vždy směrem od středu násypky)")
    schema:register(XMLValueType.NODE_INDEX, key .. ".legs.leg(?)#foot", "Patka opěry (dítě ramene, klesá)")
    schema:register(XMLValueType.NODE_INDEX, key .. ".legs.leg(?)#collision", "Kolize patky pevně ve vysunuté poloze (zapnutá jen s vysunutými opěrami)")
    schema:setXMLSpecializationType()

    local savegame = Vehicle.xmlSchemaSavegame
    savegame:register(XMLValueType.BOOL, string.format("vehicles.vehicle(?).%s.sprayDroneHopper#legsOut", SprayDroneHopper.MOD_NAME),
        "Opěry násypky jsou vysunuté")
end

function SprayDroneHopper.registerFunctions(vehicleType)
    SpecializationUtil.registerFunction(vehicleType, "sprayDroneHopperCommand", SprayDroneHopper.command)
end

function SprayDroneHopper.registerOverwrittenFunctions(vehicleType)
    SpecializationUtil.registerOverwrittenFunction(vehicleType, "getFillUnitSupportsToolType", SprayDroneHopper.getFillUnitSupportsToolType)
end

function SprayDroneHopper.registerEventListeners(vehicleType)
    SpecializationUtil.registerEventListener(vehicleType, "onLoad", SprayDroneHopper)
    SpecializationUtil.registerEventListener(vehicleType, "onDelete", SprayDroneHopper)
    SpecializationUtil.registerEventListener(vehicleType, "onUpdate", SprayDroneHopper)
    SpecializationUtil.registerEventListener(vehicleType, "onReadStream", SprayDroneHopper)
    SpecializationUtil.registerEventListener(vehicleType, "onWriteStream", SprayDroneHopper)
    SpecializationUtil.registerEventListener(vehicleType, "onReadUpdateStream", SprayDroneHopper)
    SpecializationUtil.registerEventListener(vehicleType, "onWriteUpdateStream", SprayDroneHopper)
end

function SprayDroneHopper:onLoad(savegame)
    local spec = getSpec(self)
    local xml = self.xmlFile
    local key = "vehicle.sprayDroneHopper"
    spec.limeUnit = xml:getValue(key .. "#limeFillUnitIndex", 2)
    local fineName = xml:getValue(key .. "#fineFillType", "SDT_FINE_LIME")
    spec.fineType = g_fillTypeManager:getFillTypeIndexByName(fineName) or FillType.UNKNOWN
    spec.hoseRate = math.max(xml:getValue(key .. "#hoseRate", 8), 0.01)
    spec.outlet = xml:getValue(key .. ".nodes#outlet", nil, self.components, self.i3dMappings)
    spec.outletUsedTime = -1e9
    spec.pour = {
        pourUnit = spec.limeUnit,
        pourNeck = xml:getValue(key .. ".nodes#funnel", nil, self.components, self.i3dMappings),
        pourKind = spec.fineType,
        pourBelow = 0.35,
        pourRadius = math.max(xml:getValue(key .. "#pourRadius", 0.5), 0.05),
        pourRate = math.max(xml:getValue(key .. "#pourRate", 8), 0.1),
        pourAcc = 0,
        pourTimer = 0,
    }
    spec.legTravel = xml:getValue(key .. ".legs#travel", 0.30)
    spec.legDrop = xml:getValue(key .. ".legs#drop", 0.05)
    spec.legSpeed = 1 / math.max(xml:getValue(key .. ".legs#duration", 2) * 1000, 1)
    spec.legs = {}
    xml:iterate(key .. ".legs.leg", function(_, legKey)
        local node = xml:getValue(legKey .. "#node", nil, self.components, self.i3dMappings)
        if node ~= nil then
            local x, y, z = getTranslation(node)
            local ax, _, az = localDirectionToLocal(node, getParent(node), 1, 0, 0)
            local ux, uz = SprayDroneHopper.getLegDirection(x, z, ax, az)
            local foot = xml:getValue(legKey .. "#foot", nil, self.components, self.i3dMappings)
            local leg = { node = node, x = x, y = y, z = z, dir = x >= 0 and 1 or -1, ux = ux, uz = uz, foot = foot }
            if foot ~= nil then
                leg.fx, leg.fy, leg.fz = getTranslation(foot)
            end
            leg.col = xml:getValue(legKey .. "#collision", nil, self.components, self.i3dMappings)
            if leg.col ~= nil then
                leg.colGroup, leg.colMask = getCollisionFilterGroup(leg.col), getCollisionFilterMask(leg.col)
            end
            table.insert(spec.legs, leg)
        end
    end)
    spec.legsOut = false
    spec.legsPos = 0
    spec.legsShown = -1
    spec.bagCheckTimer = 0
    spec.stoolBag = nil
    spec.dirtyFlag = self:getNextDirtyFlag()
    if savegame ~= nil and not savegame.resetVehicles and self.isServer and #spec.legs > 0 then
        spec.legsOut = savegame.xmlFile:getValue(string.format("%s.%s.sprayDroneHopper#legsOut", savegame.key, SprayDroneHopper.MOD_NAME), false)
        spec.legsPos = spec.legsOut and 1 or 0
    end
    spec.legsShown = spec.legsPos
    SprayDroneHopper.applyLegs(spec)
    SprayDroneHopper.updateFeetCollision(self)
    if self.isClient and #spec.legs > 0 and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        spec.legsActivatable = SprayDroneHopperLegsActivatable.new(self)
        g_currentMission.activatableObjectsSystem:addActivatable(spec.legsActivatable)
    end
end

function SprayDroneHopper:onDelete()
    local spec = getSpec(self)
    if spec ~= nil and spec.legsActivatable ~= nil and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        g_currentMission.activatableObjectsSystem:removeActivatable(spec.legsActivatable)
        spec.legsActivatable = nil
    end
end

function SprayDroneHopper:onUpdate(dt)
    local spec = getSpec(self)
    if self.isServer then
        SprayDroneMill.updatePour(self, dt, spec.pour)
    end
    if #spec.legs > 0 then
        local goal = spec.legsOut and 1 or 0
        if spec.legsPos ~= goal then
            spec.legsPos = goal > spec.legsPos and math.min(spec.legsPos + dt * spec.legSpeed, 1) or math.max(spec.legsPos - dt * spec.legSpeed, 0)
            self:raiseActive()
        end
        if spec.legsShown ~= spec.legsPos then
            spec.legsShown = spec.legsPos
            SprayDroneHopper.applyLegs(spec)
        end
        SprayDroneHopper.updateFeetCollision(self)
        if self.isClient and not spec.legsOut then
            spec.bagCheckTimer = spec.bagCheckTimer - dt
            if spec.bagCheckTimer <= 0 then
                spec.bagCheckTimer = SprayDroneHopper.BAG_CHECK_MS
                spec.stoolBag = SprayDroneHopper.isPlayerNear(self) and SprayDroneHopper.findStoolBag(self) or nil
            end
            if spec.stoolBag ~= nil then
                g_currentMission:addExtraPrintText(g_i18n:getText("sdt_hopper_bagLegsIn"))
            end
        end
    end
end

-- Směr vysunutí opěry v rovině (x, z) rodiče: osa x ramene (ax, az) otočená ven od středu násypky (poloha x, z); bez osy po znaménku x.
function SprayDroneHopper.getLegDirection(x, z, ax, az)
    local length = ax ~= nil and az ~= nil and math.sqrt(ax * ax + az * az) or 0
    if length < 1e-6 then
        return x >= 0 and 1 or -1, 0
    end
    ax, az = ax / length, az / length
    if ax * x + az * z < 0 then
        ax, az = -ax, -az
    end
    return ax, az
end

-- Poloha opěr 0 (zasunuté, patky nad zemí) .. 1 (vysunuté, patky na zemi): nejdřív se vysouvá rameno, pak klesá vizuální patka (dole sedí na
-- spodku pevné kolize patky, drop = výška zasunuté patky nad zemí + 1 cm).
function SprayDroneHopper.applyLegs(spec)
    local t = spec.legsPos
    local slide = math.min(t / SprayDroneHopper.LEGS_SLIDE, 1)
    local drop = math.max((t - SprayDroneHopper.LEGS_SLIDE) / (1 - SprayDroneHopper.LEGS_SLIDE), 0)
    for _, leg in ipairs(spec.legs) do
        local d = spec.legTravel * slide
        setTranslation(leg.node, leg.x + (leg.ux or leg.dir) * d, leg.y, leg.z + (leg.uz or 0) * d)
        if leg.foot ~= nil then
            setTranslation(leg.foot, leg.fx, leg.fy - spec.legDrop * drop, leg.fz)
        end
    end
end

-- Patky nesou násypku: opěry mají být venku a jsou celé vysunuté (vizuální patka dole). Při zasouvání nenesou hned od prvního snímku.
function SprayDroneHopper.getFeetCarry(spec)
    return spec.legsOut and spec.legsPos >= 1
end

-- Zapne / vypne pevné kolize patek podle getFeetCarry (na serveru i klientech: hráč chodí po kolizích u sebe). Tvary se neposouvají, mění se jen
-- filtr; tělo se pak probudí, jinak by spící násypka na nové patky nedosedla (ani z nich nesjela na rám).
function SprayDroneHopper.updateFeetCollision(self)
    local spec = getSpec(self)
    local carry = SprayDroneHopper.getFeetCarry(spec)
    if carry == spec.feetCarry then
        return
    end
    local first = spec.feetCarry == nil
    spec.feetCarry = carry
    for _, leg in ipairs(spec.legs) do
        if leg.col ~= nil and entityExists(leg.col) then
            if carry then
                setCollisionFilter(leg.col, leg.colGroup, leg.colMask)
            else
                setCollisionFilter(leg.col, 0, 0)
            end
        end
    end
    if not first and self.isServer and self.wakeUp ~= nil then
        self:wakeUp()
    end
end

-- Opěry jsou celé venku (big bag smí sypat).
function SprayDroneHopper.getLegsReady(self)
    local spec = getSpec(self)
    return #spec.legs == 0 or (spec.legsOut and spec.legsPos >= 1)
end

-- Kde leží vak vůči stolici: střed dosedacího rámu (uzel funnel je 2 cm nad ním) a kořen vaku (dno), obojí ve světě. Vrací "ok" (leží na stolici),
-- "vedle" (dál než STOOL_REACH vodorovně), "propadl" (dno pod rámem, propadl do nástavce), "nad" (nad rámem, nese ho nakladač) a vodorovnou a svislou odchylku.
SprayDroneHopper.STOOL_REACH = 0.35
function SprayDroneHopper.getStoolPlacement(fx, fy, fz, bx, by, bz)
    local horizontal = math.sqrt((bx - fx) ^ 2 + (bz - fz) ^ 2)
    local dy = by - (fy - 0.02)
    if horizontal > SprayDroneHopper.STOOL_REACH then
        return "vedle", horizontal, dy
    elseif dy < -0.06 then
        return "propadl", horizontal, dy
    elseif dy > 0.15 then
        return "nad", horizontal, dy
    end
    return "ok", horizontal, dy
end

-- Vak ležící na stolici (nebo propadlý do nástavce) této násypky: jiné vozidlo s výpustí (Dischargeable) a kořenem u rámu stolice; nil, když tam nic není.
-- Volnější než getStoolPlacement: vyprazdňující se vak se ve hře svezl až o 0,59 m stranou a 0,17 m dolů a pořád sypal. Vak na zemi je ~1,4 m pod rámem.
SprayDroneHopper.STOOL_BLOCK_REACH = 0.8
SprayDroneHopper.STOOL_BLOCK_DEPTH = 1.0
function SprayDroneHopper.findStoolBag(self)
    local spec = getSpec(self)
    local neck = spec.pour.pourNeck
    if neck == nil or not entityExists(neck) then
        return nil
    end
    local fx, fy, fz = getWorldTranslation(neck)
    local vehicles = g_currentMission.vehicleSystem ~= nil and g_currentMission.vehicleSystem.vehicles or {}
    for _, v in ipairs(vehicles) do
        if v ~= self and not v.isDeleted and v.spec_dischargeable ~= nil and v.rootNode ~= nil and entityExists(v.rootNode) then
            local bx, by, bz = getWorldTranslation(v.rootNode)
            local _, horizontal, dy = SprayDroneHopper.getStoolPlacement(fx, fy, fz, bx, by, bz)
            if horizontal <= SprayDroneHopper.STOOL_BLOCK_REACH and dy <= 0.15 and dy >= -SprayDroneHopper.STOOL_BLOCK_DEPTH then
                return v
            end
        end
    end
    return nil
end

-- Hráč pěšky do HINT_DISTANCE od násypky.
function SprayDroneHopper.isPlayerNear(self)
    local player = g_localPlayer
    if player == nil or player.getPosition == nil or (player.getCurrentVehicle ~= nil and player:getCurrentVehicle() ~= nil) then
        return false
    end
    local px, py, pz = player:getPosition()
    local x, y, z = getWorldTranslation(self.rootNode)
    return MathUtil.vector3Length(px - x, py - y, pz - z) <= SprayDroneHopper.HINT_DISTANCE
end

-- Vak (nástroj DISCHARGEABLE) sype do zásoby jen s vysunutými opěrami; pytle a hadice jdou mimo nástroje, těch se to netýká.
function SprayDroneHopper:getFillUnitSupportsToolType(superFunc, fillUnitIndex, toolType)
    local spec = getSpec(self)
    if spec ~= nil and fillUnitIndex == spec.limeUnit and toolType == ToolType.DISCHARGEABLE and not SprayDroneHopper.getLegsReady(self) then
        return false
    end
    return superFunc(self, fillUnitIndex, toolType)
end

function SprayDroneHopper.command(self, command, noEventSend)
    if SprayDroneHopperEvent.sendEvent(self, command, noEventSend) then
        return
    end
    local spec = getSpec(self)
    local out = command == SprayDroneHopper.CMD_LEGS_OUT
    if #spec.legs == 0 or out == spec.legsOut then
        return
    end
    if SprayDroneHopper.findStoolBag(self) ~= nil then
        SprayDroneSound.noteAction("násypka: opěry " .. (out and "vysunout" or "zasunout") .. " odmítnuto, na stolici leží big bag")
        return
    end
    SprayDroneSound.noteAction("násypka: opěry " .. (out and "vysunout" or "zasunout"))
    spec.legsOut = out
    self:raiseDirtyFlags(spec.dirtyFlag)
    self:raiseActive()
end

---------------------------------------------------------------------------------------------------
-- síť a uložení

function SprayDroneHopper:onWriteStream(streamId, connection)
    streamWriteBool(streamId, getSpec(self).legsOut)
end

function SprayDroneHopper:onReadStream(streamId, connection)
    local spec = getSpec(self)
    spec.legsOut = streamReadBool(streamId)
    spec.legsPos = spec.legsOut and 1 or 0
    spec.legsShown = spec.legsPos
    SprayDroneHopper.applyLegs(spec)
    SprayDroneHopper.updateFeetCollision(self)
end

function SprayDroneHopper:onWriteUpdateStream(streamId, connection, dirtyMask)
    if not connection:getIsServer() then
        local spec = getSpec(self)
        if streamWriteBool(streamId, bit32.band(dirtyMask, spec.dirtyFlag) ~= 0) then
            streamWriteBool(streamId, spec.legsOut)
        end
    end
end

function SprayDroneHopper:onReadUpdateStream(streamId, timestamp, connection)
    if connection:getIsServer() and streamReadBool(streamId) then
        getSpec(self).legsOut = streamReadBool(streamId)
        self:raiseActive()
    end
end

function SprayDroneHopper:saveToXMLFile(xmlFile, key, usedModNames)
    if getSpec(self).legsOut then
        xmlFile:setValue(key .. "#legsOut", true)
    end
end

---------------------------------------------------------------------------------------------------
-- rozhraní pro hadici vleku (stejné jako u mlýnku)

-- Výstup jemného vápna: uzel spojky, nádrž s vápnem, jeho druh a nejvyšší průtok; nil, když uzel není.
function SprayDroneHopper.getOutlet(self)
    local spec = getSpec(self)
    if spec == nil or spec.outlet == nil or not entityExists(spec.outlet) then
        return nil
    end
    return { node = spec.outlet, fillUnitIndex = spec.limeUnit, fillType = spec.fineType, rate = spec.hoseRate }
end

function SprayDroneHopper.isRunning(self)
    return SprayDronePump.isRunning(self)
end

-- Server: hadice právě přelila vápno (zvuk toku na všech klientech).
function SprayDroneHopper.markPumping(self)
    SprayDronePump.markFlow(self)
end

-- Hadice vleku hlásí každý snímek, že je na výstup připojená (u násypky bez slepé spojky jen pro úplnost rozhraní).
function SprayDroneHopper.markOutletUsed(self)
    getSpec(self).outletUsedTime = g_time
end

---------------------------------------------------------------------------------------------------
-- opěry pěšky: levé tlačítko myši u kterékoli patky

local function getPlayerPosition()
    local player = g_localPlayer
    if player == nil or (player.getCurrentVehicle ~= nil and player:getCurrentVehicle() ~= nil) or player.getPosition == nil then
        return nil
    end
    return player:getPosition()
end

-- Nejbližší patka opěry k bodu: uzel a vzdálenost.
local function nearestFoot(spec, x, y, z)
    local best, bestDistance = nil, math.huge
    for _, leg in ipairs(spec.legs) do
        local node = leg.foot or leg.node
        if entityExists(node) then
            local nx, ny, nz = getWorldTranslation(node)
            local d = MathUtil.vector3Length(x - nx, y - ny, z - nz)
            if d < bestDistance then
                best, bestDistance = node, d
            end
        end
    end
    return best, bestDistance
end

SprayDroneHopperLegsActivatable = {}
local SprayDroneHopperLegsActivatable_mt = Class(SprayDroneHopperLegsActivatable)

function SprayDroneHopperLegsActivatable.new(vehicle)
    local self = setmetatable({}, SprayDroneHopperLegsActivatable_mt)
    self.vehicle = vehicle
    self.activateText = g_i18n:getText("sdt_hopper_legsOut")
    return self
end

function SprayDroneHopperLegsActivatable:getIsActivatable()
    local vehicle = self.vehicle
    if vehicle.isDeleted or g_localPlayer == nil or not g_currentMission.accessHandler:canFarmAccess(g_localPlayer.farmId, vehicle) then
        return false
    end
    if VehiclePropertyState ~= nil and vehicle.propertyState == VehiclePropertyState.SHOP_CONFIG then
        return false
    end
    local px, py, pz = getPlayerPosition()
    if px == nil then
        return false
    end
    local spec = getSpec(vehicle)
    local _, distance = nearestFoot(spec, px, py, pz)
    if distance > SprayDroneHopper.LEGS_DISTANCE then
        return false
    end
    self.activateText = g_i18n:getText(spec.legsOut and "sdt_hopper_legsIn" or "sdt_hopper_legsOut")
    if self.clickEventId ~= nil then
        g_inputBinding:setActionEventText(self.clickEventId, self.activateText)
        g_inputBinding:setActionEventTextVisibility(self.clickEventId, SprayDroneLink.mayClick(self))
    end
    return true
end

function SprayDroneHopperLegsActivatable:getDistance(x, y, z)
    local node, distance = nearestFoot(getSpec(self.vehicle), x, y, z)
    return SprayDroneLink.aimDistance(distance, node)
end

function SprayDroneHopperLegsActivatable:registerCustomInput(inputContext)
    self.clickEventId = SprayDroneLink.registerClick(self, self.run, self.activateText)
    SprayDroneLink.setSelected(self, true)
end

function SprayDroneHopperLegsActivatable:removeCustomInput(inputContext)
    g_inputBinding:removeActionEventsByTarget(self)
    SprayDroneLink.setSelected(self, false)
    self.clickEventId = nil
end

function SprayDroneHopperLegsActivatable:run()
    if not SprayDroneLink.mayClick(self) then
        return
    end
    SprayDroneSound.noteAction("násypka: levé tlačítko myši u opěry")
    if SprayDroneHopper.findStoolBag(self.vehicle) ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText("sdt_hopper_legsBag"), 2500)
        return
    end
    local spec = getSpec(self.vehicle)
    self.vehicle:sprayDroneHopperCommand(spec.legsOut and SprayDroneHopper.CMD_LEGS_IN or SprayDroneHopper.CMD_LEGS_OUT)
end

function SprayDroneHopperLegsActivatable:activate() end

function SprayDroneHopperLegsActivatable:deactivate() end

function SprayDroneHopperLegsActivatable:draw() end
