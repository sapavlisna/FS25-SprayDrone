-- Spojení s dronem: přenosná relé tyč a mobilní vysílačka (tablet).
--
-- Dosah dronu je dosah rádia vleku (sprayDrone#maxRange, s anténou vyšší). Relé tyč (objects/relay/relayPole.xml, SprayDroneRelay.lua:
-- rozložená, zapnutá, stojí vzpřímená a nikdo ji nedrží) ho prodlouží: počítá se kruh o poloměru dosah + vzdálenost relé od vleku, když je relé samo
-- v dosahu vleku (zjednodušení: kruh kolem vleku, ne sjednocení dvou kruhů). Tablet (objects/tablet/droneTablet.xml, ruční nástroj jako baterka) drží
-- hráč v ruce a klávesou R jím otevře plánovač rozloženého vleku, který je v dosahu; jinak je vidět NO CONNECTION.
-- Hráč je ve spojení, když je v dosahu rádia vleku, nebo aktivního relé, které je s vlekem spojené.
-- Na vleku je pevný displej (i3dMapping plannerScreenNode, osa +Z ven z obrazovky): pěší hráč u něj otevře plánovač (levé tlačítko myši, INTERACT),
-- plánovač se zavře, když od displeje odejde nebo se vlek složí.
--
-- Pojistky signálu: dávka, jejíž trasa vede mimo rádio vleku, závisí na tyčích (getNeededRelays); před odletem musí mít
-- každá výdrž na dávku s rezervou (getRelayRequiredSeconds), tyč, na které závisí letící dron, nejde složit ani vypnout
-- (getRelayBlockReason, registruje se do SprayDroneRelay.registerBlockCheck).

SprayDroneLink = {}

SprayDroneLink.RELAY_FILE = "relayPole.xml"
SprayDroneLink.TABLET_FILE = "droneTablet.xml"
SprayDroneLink.RELAY_MIN_UP = 0.8     -- svislá složka osy tyče: stojí vzpřímeně
SprayDroneLink.RELAY_RADIUS = 300      -- vlastní dosah tyče (m), pokud není v obchodě vybraná silnější varianta
SprayDroneLink.RELAY_RESERVE_FACTOR = 1.5  -- výdrž tyče před odletem dávky: aspoň čas dávky × tolik
SprayDroneLink.RELAY_MIN_RESERVE = 300     -- a aspoň o tolik s víc než čas dávky
SprayDroneLink.SCREEN_NODE = "plannerScreenNode"
SprayDroneLink.SCREEN_DISTANCE = 1.6       -- m od displeje (vodorovně), odkud jde plánovač otevřít
SprayDroneLink.SCREEN_CLOSE_DISTANCE = 4   -- dál se otevřený plánovač zavře
SprayDroneLink.SCREEN_BELOW = 2.6          -- hráč (poloha u nohou) smí být nejvýš tolik m pod displejem
SprayDroneLink.SCREEN_BEHIND = 0.3         -- a nejvýš tolik m za jeho rovinou (stojí před obrazovkou)

local function hasFile(object, file)
    local name = object ~= nil and object.configFileName or nil
    if type(name) ~= "string" then
        return false
    end
    name = string.lower(name)
    file = string.lower(file)
    return string.sub(name, -#file) == file
end

local function getVehicles()
    local system = g_currentMission ~= nil and g_currentMission.vehicleSystem or nil
    return system ~= nil and system.vehicles or {}
end

-- Uzly, které hráči drží v rukou (HandToolHands.spec_hands.heldItemNode), jako množina.
local function getHeldNodes()
    local held = {}
    local players = {}
    if g_localPlayer ~= nil then
        players[1] = g_localPlayer
    end
    for _, player in ipairs(players) do
        local hands = player.hands
        local handsSpec = hands ~= nil and hands.spec_hands or nil
        if handsSpec ~= nil and handsSpec.heldItemNode ~= nil then
            held[handsSpec.heldItemNode] = true
        end
    end
    return held
end

local function isHeld(vehicle, held)
    if held[vehicle.rootNode] then
        return true
    end
    for _, component in ipairs(vehicle.components or {}) do
        if held[component.node] then
            return true
        end
    end
    return false
end

-- Je relé aktivní? Rozložené, zapnuté, vzpřímené (SprayDroneRelay.isOperating) a nikdo ho nedrží ani nenese.
function SprayDroneLink.isRelayActive(vehicle, held)
    if vehicle.isDeleted or vehicle.rootNode == nil or not entityExists(vehicle.rootNode) or isHeld(vehicle, held or getHeldNodes()) then
        return false
    end
    if vehicle.getDynamicMountObject ~= nil and vehicle:getDynamicMountObject() ~= nil then
        return false
    end
    if SprayDroneRelay ~= nil and vehicle[SprayDroneRelay.SPEC_NAME] ~= nil then
        return SprayDroneRelay.isOperating(vehicle)
    end
    local _, upY = localDirectionToWorld(vehicle.rootNode, 0, 1, 0)
    return upY >= SprayDroneLink.RELAY_MIN_UP
end

-- Dosah tyče (m) podle varianty v obchodě; bez specializace (test, nebo chybějící data) výchozí.
function SprayDroneLink.getRelayRadius(vehicle)
    local relaySpec = SprayDroneRelay ~= nil and vehicle[SprayDroneRelay.SPEC_NAME] or nil
    return relaySpec ~= nil and relaySpec.radius or SprayDroneLink.RELAY_RADIUS
end

function SprayDroneLink.getActiveRelays()
    local held = getHeldNodes()
    local relays = {}
    for _, vehicle in ipairs(getVehicles()) do
        if hasFile(vehicle, SprayDroneLink.RELAY_FILE) and SprayDroneLink.isRelayActive(vehicle, held) then
            local x, _, z = getWorldTranslation(vehicle.rootNode)
            table.insert(relays, { x = x, z = z, radius = SprayDroneLink.getRelayRadius(vehicle), vehicle = vehicle })
        end
    end
    return relays
end

-- Všechny tyče na mapě (i složené a vypnuté) pro ikony v plánovači: x, z, dosah a jestli je aktivní.
function SprayDroneLink.getRelays()
    local held = getHeldNodes()
    local relays = {}
    for _, vehicle in ipairs(getVehicles()) do
        if hasFile(vehicle, SprayDroneLink.RELAY_FILE) and not vehicle.isDeleted and vehicle.rootNode ~= nil and entityExists(vehicle.rootNode) then
            local x, _, z = getWorldTranslation(vehicle.rootNode)
            table.insert(relays, { x = x, z = z, radius = SprayDroneLink.getRelayRadius(vehicle), active = SprayDroneLink.isRelayActive(vehicle, held) })
        end
    end
    return relays
end

local function distance2D(ax, az, bx, bz)
    return math.sqrt((ax - bx) ^ 2 + (az - bz) ^ 2)
end

local TWO_PI = 2 * math.pi
local EPS = 1e-6

-- Obrys sjednocení kruhů {x, z, r}: úsečky {x1, z1, x2, z2, circle = index kruhu}, jen z úseků, které neleží uvnitř jiného
-- kruhu. Kruh se rozdělí v průsečících s ostatními na oblouky, oblouk se bere podle svého středu; plný kruh má `segments` úseček.
-- Shodné kruhy se kreslí jen jednou (ten s nižším indexem).
function SprayDroneLink.getCoverageArcs(circles, segments)
    segments = segments or 96
    local lines = {}
    for i, c in ipairs(circles) do
        local hidden = c.r <= 0
        local cuts = { 0, TWO_PI }
        for j, o in ipairs(circles) do
            if j ~= i and not hidden and o.r > 0 then
                local d = distance2D(c.x, c.z, o.x, o.z)
                local same = d < EPS and math.abs(c.r - o.r) < EPS
                if (same and j < i) or (not same and d + c.r <= o.r + EPS) then
                    hidden = true
                elseif not same and d > EPS and d < c.r + o.r and d > math.abs(c.r - o.r) then
                    local base = math.atan2(o.z - c.z, o.x - c.x)
                    local half = math.acos(math.max(-1, math.min(1, (c.r * c.r + d * d - o.r * o.r) / (2 * c.r * d))))
                    for _, a in ipairs({ base - half, base + half }) do
                        table.insert(cuts, a % TWO_PI)
                    end
                end
            end
        end
        if not hidden then
            table.sort(cuts)
            for k = 1, #cuts - 1 do
                local a1, a2 = cuts[k], cuts[k + 1]
                if a2 - a1 > EPS then
                    local mid = (a1 + a2) * 0.5
                    local mx, mz = c.x + math.cos(mid) * c.r, c.z + math.sin(mid) * c.r
                    local inside = false
                    for j, o in ipairs(circles) do
                        if j ~= i and o.r > 0 and distance2D(mx, mz, o.x, o.z) < o.r - EPS then
                            inside = true
                            break
                        end
                    end
                    if not inside then
                        local n = math.max(1, math.ceil(segments * (a2 - a1) / TWO_PI))
                        for s = 0, n - 1 do
                            local b1, b2 = a1 + (a2 - a1) * s / n, a1 + (a2 - a1) * (s + 1) / n
                            table.insert(lines, { x1 = c.x + math.cos(b1) * c.r, z1 = c.z + math.sin(b1) * c.r,
                                x2 = c.x + math.cos(b2) * c.r, z2 = c.z + math.sin(b2) * c.r, circle = i })
                        end
                    end
                end
            end
        end
    end
    return lines
end

-- Kruhy signálu vleku pro obrys: rádio vleku (index 1) a každá aktivní tyč, která je s vlekem spojená (jako isConnected).
function SprayDroneLink.getSignalCircles(vehicle)
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    local hx, hz = SprayDroneStation.getHomePosition(vehicle)
    local circles = { { x = hx, z = hz, r = spec.maxRange } }
    for _, relay in ipairs(SprayDroneLink.getActiveRelays()) do
        if distance2D(hx, hz, relay.x, relay.z) <= spec.maxRange then
            table.insert(circles, { x = relay.x, z = relay.z, r = relay.radius })
        end
    end
    return circles
end

-- O kolik metrů relé prodlužují dosah vleku: vzdálenost nejvzdálenějšího aktivního relé, které je v dosahu rádia vleku (`radio`).
function SprayDroneLink.getRangeBonus(vehicle, radio)
    local hx, hz = SprayDroneStation.getHomePosition(vehicle)
    local bonus = 0
    for _, relay in ipairs(SprayDroneLink.getActiveRelays()) do
        local d = distance2D(hx, hz, relay.x, relay.z)
        if d <= radio and d > bonus then
            bonus = d
        end
    end
    return bonus
end

-- Je bod (x, z) ve spojení s vlekem? Rádio vleku, nebo aktivní relé spojené s vlekem.
function SprayDroneLink.isConnected(vehicle, x, z)
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    local radio = spec.maxRange
    local hx, hz = SprayDroneStation.getHomePosition(vehicle)
    if distance2D(hx, hz, x, z) <= radio then
        return true
    end
    for _, relay in ipairs(SprayDroneLink.getActiveRelays()) do
        if distance2D(hx, hz, relay.x, relay.z) <= radio and distance2D(relay.x, relay.z, x, z) <= relay.radius then
            return true
        end
    end
    return false
end

---------------------------------------------------------------------------------------------------
-- pojistky signálu (čisté funkce: tmp/f/test_signal.lua)

-- Leží bod (x, z) v některém z kruhů {x, z, r}? margin (m) kruhy zvětší.
function SprayDroneLink.isInCircles(circles, x, z, margin)
    margin = margin or 0
    for _, c in ipairs(circles) do
        if distance2D(c.x, c.z, x, z) <= c.r + margin then
            return true
        end
    end
    return false
end

-- Tyče, na kterých dávka závisí: ty z relays ({x, z, radius, ...}, spojené s vlekem), v jejichž kruhu leží některý bod trasy
-- (points {x, z}; body bez x se přeskočí) mimo rádio vleku (střed hx, hz, poloměr radio). Bod pokrytý víc tyčemi zaváže všechny.
function SprayDroneLink.getNeededRelays(points, hx, hz, radio, relays)
    local needed, used = {}, {}
    for _, p in ipairs(points) do
        if p.x ~= nil and p.z ~= nil and distance2D(hx, hz, p.x, p.z) > radio then
            for i, relay in ipairs(relays) do
                if not used[i] and distance2D(relay.x, relay.z, p.x, p.z) <= relay.radius then
                    used[i] = true
                    table.insert(needed, relay)
                end
            end
        end
    end
    return needed
end

-- Kolik s musí tyč ještě vydržet, aby dron dávku (batchSeconds) bezpečně odletěl: čas × RELAY_RESERVE_FACTOR, nejméně čas + RELAY_MIN_RESERVE.
function SprayDroneLink.getRelayRequiredSeconds(batchSeconds)
    batchSeconds = math.max(batchSeconds or 0, 0)
    return math.max(batchSeconds * SprayDroneLink.RELAY_RESERVE_FACTOR, batchSeconds + SprayDroneLink.RELAY_MIN_RESERVE)
end

-- První tyč z relays, jejíž výdrž (relay.remaining v s; nil = bez baterie, neomezená) na dávku nestačí; nil = stačí všechny.
function SprayDroneLink.getShortRelay(relays, batchSeconds)
    local required = SprayDroneLink.getRelayRequiredSeconds(batchSeconds)
    for _, relay in ipairs(relays) do
        if relay.remaining ~= nil and relay.remaining < required then
            return relay
        end
    end
    return nil
end

-- Potřebuje tyč relay ({x, z, radius, vehicle}) některý dron? drones = { {relays = vozidla tyčí, na kterých závisí jeho dávka,
-- x, z = poloha dronu ve vzduchu (nil na vleku), others = kruhy signálu jeho vleku bez této tyče (rádio vleku a ostatní tyče)} }.
-- Ano, když na ní závisí jeho dávka, nebo je dron v jejím kruhu a jinde signál nemá.
function SprayDroneLink.isRelayNeeded(relay, drones)
    for _, d in ipairs(drones) do
        for _, used in ipairs(d.relays or {}) do
            if used == relay.vehicle then
                return true
            end
        end
        if d.x ~= nil and distance2D(relay.x, relay.z, d.x, d.z) <= relay.radius and not SprayDroneLink.isInCircles(d.others or {}, d.x, d.z) then
            return true
        end
    end
    return false
end

-- Stojí hráč u displeje? lx, ly, lz = poloha hráče (u nohou) v souřadnicích uzlu displeje (+Z ven z obrazovky, +Y nahoru);
-- distance = vodorovná vzdálenost, do které platí.
function SprayDroneLink.isAtScreen(lx, ly, lz, distance)
    return math.sqrt(lx * lx + lz * lz) <= distance and lz >= -SprayDroneLink.SCREEN_BEHIND
        and ly >= -SprayDroneLink.SCREEN_BELOW and ly <= 1
end

-- Pořadí vleků pro tablet (čistá funkce, tmp/f/test_tablet_logo.lua): entries {distance, inRange, missionActive, unfolded, ...}.
-- Nejdřív vleky v dosahu signálu (inRange: s dronem a ve spojení) - s puštěnou misí, pak rozložené, pak ostatní; za nimi vleky
-- mimo dosah. Uvnitř skupiny rozhoduje vzdálenost. Seřadí entries na místě a vrátí je.
function SprayDroneLink.getTrailerGroup(e)
    if not e.inRange then
        return 4
    end
    if e.missionActive then
        return 1
    end
    return e.unfolded and 2 or 3
end

function SprayDroneLink.rankTrailers(entries)
    table.sort(entries, function(a, b)
        local ga, gb = SprayDroneLink.getTrailerGroup(a), SprayDroneLink.getTrailerGroup(b)
        if ga ~= gb then
            return ga < gb
        end
        return a.distance < b.distance
    end)
    return entries
end

-- Design pro logo tabletu ze seřazených entries (první vlek, i mimo dosah); bez vleku výchozí.
function SprayDroneLink.pickLogoDesign(entries)
    local first = entries[1]
    return first ~= nil and first.design or SprayDroneLink.DEFAULT_DESIGN
end

-- Běží na vleku mise (u Maxu u kteréhokoli z dronů)?
local function isMissionActive(vehicle)
    if SprayDroneDrones ~= nil and SprayDroneDrones.getCount ~= nil then
        for k = 1, SprayDroneDrones.getCount(vehicle) do
            local d = SprayDroneDrones.getSpec(vehicle, k)
            if d ~= nil and d.missionActive then
                return true
            end
        end
        return false
    end
    return vehicle[SprayDroneStation.SPEC_NAME].missionActive == true
end

-- Všechny vleky, které farma smí používat, seřazené rankTrailers vzhledem k bodu (x, z).
function SprayDroneLink.collectTrailers(x, z, farmId)
    local result = {}
    for _, vehicle in ipairs(getVehicles()) do
        local spec = vehicle[SprayDroneStation.SPEC_NAME]
        if spec ~= nil and not vehicle.isDeleted
            and (farmId == nil or g_currentMission.accessHandler:canFarmAccess(farmId, vehicle)) then
            local hx, hz = SprayDroneStation.getHomePosition(vehicle)
            table.insert(result, { vehicle = vehicle, distance = distance2D(hx, hz, x, z),
                inRange = spec.hasDrone == true and SprayDroneLink.isConnected(vehicle, x, z),
                missionActive = isMissionActive(vehicle),
                unfolded = vehicle.getIsUnfolded ~= nil and vehicle:getIsUnfolded() == true,
                design = SprayDroneLink.getVehicleDesign(vehicle) })
        end
    end
    return SprayDroneLink.rankTrailers(result)
end

-- Vleky s dronem ve spojení s bodem (x, z) v pořadí rankTrailers (mise, rozložené, ostatní; od nejbližšího); farma hráče
-- musí vlek smět používat. Tablet otevře plánovač i u složeného vleku (plánovat jde, start letu hlídá vlek sám).
function SprayDroneLink.findTrailers(x, z, farmId)
    local result = {}
    for _, e in ipairs(SprayDroneLink.collectTrailers(x, z, farmId)) do
        if e.inRange then
            table.insert(result, e)
        end
    end
    return result
end

-- Logo designu na tabletu: polepy brand_<KEY>_tablet v i3d tabletu, vidět je ten designu vleku, ke kterému by se tablet právě
-- připojil (první z collectTrailers - stejné pořadí jako openTablet), mimo dosah nejbližšího vleku farmy, bez vleku BZUK.
-- Jen vizuál u místního hráče (konfigurace vozidel zná i klient), kontrola jednou za TABLET_LOGO_INTERVAL s tabletem v ruce.
SprayDroneLink.DESIGN_KEYS = { "BZUK", "ROSA", "KAPKA", "STRATUS" }
SprayDroneLink.DEFAULT_DESIGN = "BZUK"
SprayDroneLink.TABLET_BRAND_PLACE = "tablet"
SprayDroneLink.TABLET_LOGO_INTERVAL = 1000

-- Klíč designu vozidla: vehicle.configurations.design (index) -> storeItem.configurations.design[index].saveId (BZUK, ROSA ...).
function SprayDroneLink.getVehicleDesign(vehicle)
    local index = vehicle.configurations ~= nil and vehicle.configurations.design or nil
    local storeItem = index ~= nil and g_storeManager ~= nil and g_storeManager:getItemByXMLFilename(vehicle.configFileName) or nil
    local items = storeItem ~= nil and storeItem.configurations ~= nil and storeItem.configurations.design or nil
    local item = items ~= nil and items[index] or nil
    local key = item ~= nil and item.saveId or nil
    for _, k in ipairs(SprayDroneLink.DESIGN_KEYS) do
        if k == key then
            return key
        end
    end
    return SprayDroneLink.DEFAULT_DESIGN
end

-- Tablet, který drží místní hráč (nebo nil). Tablet je ruční nástroj (objects/tablet/droneTablet.xml, handTool type base).
function SprayDroneLink.getHeldTablet()
    local player = g_localPlayer
    local tool = player ~= nil and player.getHeldHandTool ~= nil and player:getHeldHandTool() or nil
    if tool ~= nil and hasFile(tool, SprayDroneLink.TABLET_FILE) then
        return tool
    end
    return nil
end

local function getPlayerPosition()
    local player = g_localPlayer
    if player == nil or player.getPosition == nil then
        return nil
    end
    return player:getPosition()
end

-- Hráč ve spojení s vlekem (tablet režim plánovače).
function SprayDroneLink.isPlayerConnected(vehicle)
    local x, _, z = getPlayerPosition()
    return x ~= nil and SprayDroneLink.isConnected(vehicle, x, z)
end

function SprayDroneLink.openTablet()
    local x, _, z = getPlayerPosition()
    if x == nil then
        return
    end
    local found = SprayDroneLink.findTrailers(x, z, g_currentMission:getFarmId())
    if #found == 0 then
        g_currentMission:showBlinkingWarning(g_i18n:getText("sdt_tablet_noConnection"), 2500)
        return
    end
    local tool = SprayDroneLink.getHeldTablet()
    if tool ~= nil then
        tool.sdtScreenWake = g_time
    end
    SprayDronePlannerScreen.show(found[1].vehicle, SprayDronePlannerScreen.MODE_TABLET)
end

---------------------------------------------------------------------------------------------------
-- pojistky signálu ve hře

-- Zbývající výdrž tyče (reálné s) podle SprayDroneRelay; nil = tyč baterii nemá (nebo ji neumí říct).
function SprayDroneLink.getRelayRemaining(relayVehicle)
    if SprayDroneRelay ~= nil and SprayDroneRelay.getRemainingSeconds ~= nil and relayVehicle ~= nil then
        return SprayDroneRelay.getRemainingSeconds(relayVehicle)
    end
    return nil
end

-- Aktivní tyče spojené s vlekem (v rádiu vleku, v kontextu dronu), s vozidlem a zbývající výdrží (remaining).
function SprayDroneLink.getConnectedRelays(vehicle)
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    local hx, hz = SprayDroneStation.getHomePosition(vehicle)
    local relays = {}
    for _, relay in ipairs(SprayDroneLink.getActiveRelays()) do
        if distance2D(hx, hz, relay.x, relay.z) <= spec.maxRange then
            relay.remaining = SprayDroneLink.getRelayRemaining(relay.vehicle)
            table.insert(relays, relay)
        end
    end
    return relays
end

-- Proč tyč nejde složit / vypnout (klíč textu), nebo nil. Volá ji SprayDroneRelay před složením a vypnutím (registerBlockCheck).
function SprayDroneLink.getRelayBlockReason(relayVehicle, action)
    if relayVehicle == nil or relayVehicle.isDeleted or relayVehicle.rootNode == nil or not entityExists(relayVehicle.rootNode) then
        return nil
    end
    local x, _, z = getWorldTranslation(relayVehicle.rootNode)
    local relay = { x = x, z = z, radius = SprayDroneLink.getRelayRadius(relayVehicle), vehicle = relayVehicle }
    local drones = {}
    for _, vehicle in ipairs(getVehicles()) do
        local root = vehicle[SprayDroneStation.SPEC_NAME]
        if root ~= nil and root.hasDrone and not vehicle.isDeleted then
            for k = 1, SprayDroneDrones.getCount(vehicle) do
                local d = SprayDroneDrones.getSpec(vehicle, k)
                if d ~= nil and (d.state == SprayDroneStation.STATE_FLYING or d.state == SprayDroneStation.STATE_RETURNING) then
                    local entry = { relays = d.batchRelays }
                    if d.node ~= nil and not d.isLinked and entityExists(d.node) then
                        entry.x, _, entry.z = getWorldTranslation(d.node)
                        entry.others = {}
                        for _, c in ipairs(SprayDroneDrones.runAs(vehicle, k, SprayDroneLink.getSignalCircles)) do
                            if distance2D(c.x, c.z, x, z) > 0.01 then
                                table.insert(entry.others, c)
                            end
                        end
                    end
                    table.insert(drones, entry)
                end
            end
        end
    end
    if SprayDroneLink.isRelayNeeded(relay, drones) then
        return "sdt_relay_blockedDrone"
    end
    return nil
end

---------------------------------------------------------------------------------------------------
-- displej plánovače na vleku

-- Stojí místní hráč (pěšky) u displeje vleku do vodorovné vzdálenosti distance? Bez uzlu displeje vždy ne.
function SprayDroneLink.isPlayerAtScreen(vehicle, distance)
    local spec = SprayDroneDrones.getRoot(vehicle)
    local node = spec ~= nil and spec.plannerScreenNode or nil
    local player = g_localPlayer
    if node == nil or not entityExists(node) or player == nil then
        return false
    end
    if player.getCurrentVehicle ~= nil and player:getCurrentVehicle() ~= nil then
        return false
    end
    local px, py, pz = getPlayerPosition()
    if px == nil then
        return false
    end
    local lx, ly, lz = worldToLocal(node, px, py, pz)
    return SprayDroneLink.isAtScreen(lx, ly, lz, distance)
end

-- Může místní hráč (pěšky) otevřít plánovač u displeje tohoto vleku?
function SprayDroneLink.canUseScreen(vehicle)
    if vehicle == nil or vehicle.isDeleted or g_localPlayer == nil then
        return false
    end
    if VehiclePropertyState ~= nil and vehicle.propertyState == VehiclePropertyState.SHOP_CONFIG then
        return false
    end
    local spec = SprayDroneDrones.getRoot(vehicle)
    if spec == nil or spec.plannerScreenNode == nil or not spec.hasDrone
        or not g_currentMission.accessHandler:canFarmAccess(g_localPlayer.farmId, vehicle) then
        return false
    end
    -- složený vlek má displej pod plachtou / bednou; plánovač pak jde jen přes tablet
    if vehicle.getIsUnfolded ~= nil and not vehicle:getIsUnfolded() then
        return false
    end
    return SprayDroneLink.isPlayerAtScreen(vehicle, SprayDroneLink.SCREEN_DISTANCE)
end

-- Displej vleku (vlek načítá SprayDroneStation:onLoad): uzel z i3dMapping; bez uzlu se displej nenabízí.
function SprayDroneLink.loadScreen(vehicle)
    local spec = SprayDroneDrones.getRoot(vehicle)
    spec.plannerScreenNode = SprayDroneStation.getMappedNode(vehicle, SprayDroneLink.SCREEN_NODE)
    spec.plannerScreenOn = SprayDroneStation.getMappedNode(vehicle, SprayDroneLink.SCREEN_ON_NODE)
    spec.screenWakeTime = g_time or 0
end

---------------------------------------------------------------------------------------------------
-- zhasínání obrazovek: displej vleku i tablet v ruce po SCREEN_SLEEP_MS (reálný čas) bez použití zhasne (skryje se svítící
-- obsah, i3dMapping plannerScreenOn / uzel tabletScreenOn); otevření plánovače, nebo když je plánovač otevřený, ho rozsvítí.

SprayDroneLink.SCREEN_ON_NODE = "plannerScreenOn"
SprayDroneLink.TABLET_SCREEN_ON_NODE = "tabletScreenOn"
SprayDroneLink.SCREEN_SLEEP_MS = 10 * 60 * 1000

-- Svítí obrazovka, rozsvícená naposledy v čase wakeTime?
function SprayDroneLink.isScreenAwake(wakeTime, now)
    return wakeTime ~= nil and now - wakeTime < SprayDroneLink.SCREEN_SLEEP_MS
end

local function findChildByName(node, name)
    if node == nil or node == 0 then
        return nil
    end
    if getName(node) == name then
        return node
    end
    for i = 0, getNumOfChildren(node) - 1 do
        local found = findChildByName(getChildAt(node, i), name)
        if found ~= nil then
            return found
        end
    end
    return nil
end

local function setScreenVisible(holder, node, visible)
    if node ~= nil and holder.sdtScreenShown ~= visible and entityExists(node) then
        holder.sdtScreenShown = visible
        setVisibility(node, visible)
    end
end

-- Kterému vleku teď patří otevřený plánovač (nebo nil).
local function getPlannerVehicle()
    local screen = SprayDronePlannerScreen ~= nil and SprayDronePlannerScreen.INSTANCE or nil
    if screen ~= nil and screen.getIsOpen ~= nil and screen:getIsOpen() then
        return screen.vehicle
    end
    return nil
end

function SprayDroneLink.updateTabletLogo(tool, now)
    if tool.sdtBrandNodes == nil then
        tool.sdtBrandNodes = {}
        local root = tool.graphicalNode or tool.rootNode
        for _, key in ipairs(SprayDroneLink.DESIGN_KEYS) do
            tool.sdtBrandNodes[key] = findChildByName(root, "brand_" .. key .. "_" .. SprayDroneLink.TABLET_BRAND_PLACE)
        end
    end
    if tool.sdtLogoTime ~= nil and now - tool.sdtLogoTime < SprayDroneLink.TABLET_LOGO_INTERVAL then
        return
    end
    tool.sdtLogoTime = now
    local x, _, z = getPlayerPosition()
    local design = SprayDroneLink.DEFAULT_DESIGN
    if x ~= nil and g_currentMission ~= nil then
        design = SprayDroneLink.pickLogoDesign(SprayDroneLink.collectTrailers(x, z, g_currentMission:getFarmId()))
    end
    if design ~= tool.sdtLogoDesign then
        tool.sdtLogoDesign = design
        for key, node in pairs(tool.sdtBrandNodes) do
            if entityExists(node) then
                setVisibility(node, key == design)
            end
        end
    end
end

function SprayDroneLink.updateScreens()
    local now = g_time or 0
    local plannerVehicle = getPlannerVehicle()
    for _, vehicle in ipairs(getVehicles()) do
        local spec = vehicle[SprayDroneStation.SPEC_NAME]
        if spec ~= nil and spec.plannerScreenOn ~= nil then
            if plannerVehicle == vehicle then
                spec.screenWakeTime = now
            end
            setScreenVisible(spec, spec.plannerScreenOn, SprayDroneLink.isScreenAwake(spec.screenWakeTime, now))
        end
    end
    local tool = SprayDroneLink.getHeldTablet()
    if tool ~= nil then
        if tool.sdtScreenOn == nil then
            tool.sdtScreenOn = findChildByName(tool.graphicalNode or tool.rootNode, SprayDroneLink.TABLET_SCREEN_ON_NODE) or false
            tool.sdtScreenWake = now
        end
        if plannerVehicle ~= nil then
            tool.sdtScreenWake = now
        end
        if tool.sdtScreenOn then
            setScreenVisible(tool, tool.sdtScreenOn, SprayDroneLink.isScreenAwake(tool.sdtScreenWake, now))
        end
        SprayDroneLink.updateTabletLogo(tool, now)
    end
end

function SprayDroneLink.deleteScreen(vehicle)
end

---------------------------------------------------------------------------------------------------
-- ovládání pěšky myší (vlastní akce v kontextu hráče, ne ActivatableObjectsSystem – ten nabízí jen jednu nejbližší aktivaci a
-- na Mini by displej přebil bednu na R): tablet v ruce = R (ACTIVATE_OBJECT), displej vleku a elektrocentrála
-- = INTERACT (levé tlačítko, jako vanilla vypínače světel).

-- Co se teď dá ovládat: "tablet", nebo "screen" + vlek; nil = nic.
function SprayDroneLink.getOpenTarget()
    local player = g_localPlayer
    if player == nil or g_gui:getIsGuiVisible() or (player.getCurrentVehicle ~= nil and player:getCurrentVehicle() ~= nil) then
        return nil
    end
    if SprayDroneLink.getHeldTablet() ~= nil then
        return "tablet"
    end
    local x, _, z = getPlayerPosition()
    local bestKind, bestVehicle, bestDistance = nil, nil, math.huge
    for _, vehicle in ipairs(getVehicles()) do
        local spec = vehicle[SprayDroneStation.SPEC_NAME]
        if spec ~= nil then
            if spec.plannerScreenNode ~= nil and SprayDroneLink.canUseScreen(vehicle) then
                local nx, _, nz = getWorldTranslation(spec.plannerScreenNode)
                local d = x ~= nil and distance2D(x, z, nx, nz) or 0
                if d < bestDistance then
                    bestKind, bestVehicle, bestDistance = "screen", vehicle, d
                end
            end
        end
    end
    return bestKind, bestVehicle
end

SprayDroneLink.OPEN_REPEAT_MS = 300   -- akce i přímé kliknutí myší můžou přijít ze stejného stisku, otevře se jen jednou

function SprayDroneLink:onPlayerAction()
    if self.lastOpenTime ~= nil and g_time - self.lastOpenTime < SprayDroneLink.OPEN_REPEAT_MS then
        return
    end
    self.lastOpenTime = g_time
    if self.openKind == "tablet" then
        SprayDroneLink.openTablet()
    elseif self.openKind == "screen" and self.openVehicle ~= nil then
        SprayDroneDrones.getRoot(self.openVehicle).screenWakeTime = g_time
        SprayDronePlannerScreen.show(self.openVehicle, SprayDronePlannerScreen.MODE_SCREEN)
    end
end

-- Displej se otevírá i přímým levým kliknutím: akci INTERACT na levém tlačítku u Mini a Middle přebíjí jiná akce na stejném
-- tlačítku (zvedání předmětů rukama u hadice / centrály), kliknutí pak nic neudělalo.
function SprayDroneLink:mouseEvent(posX, posY, isDown, isUp, button)
    if isDown and button == Input.MOUSE_BUTTON_LEFT and self.openKind == "screen" and self.openVehicle ~= nil
        and g_gui ~= nil and not g_gui:getIsGuiVisible() then
        self:onPlayerAction()
    end
end

function SprayDroneLink:update(dt)
    if g_client ~= nil then
        SprayDroneLink.updateScreens()
    end
    if g_inputBinding == nil or PlayerInputComponent == nil then
        return
    end
    local kind, vehicle = SprayDroneLink.getOpenTarget()
    self.openKind, self.openVehicle = kind, vehicle
    local action = nil
    if kind == "tablet" then
        action = InputAction.ACTIVATE_OBJECT
    elseif kind ~= nil then
        action = InputAction.INTERACT
    end
    if self.openEventId ~= nil and self.openAction ~= action then
        SprayDroneLink.removeOpenAction(self)
    end
    if action ~= nil and self.openEventId == nil then
        g_inputBinding:beginActionEventsModification(PlayerInputComponent.INPUT_CONTEXT_NAME)
        local _, eventId = g_inputBinding:registerActionEvent(action, self, self.onPlayerAction, false, true, false, true)
        g_inputBinding:endActionEventsModification()
        self.openEventId, self.openAction = eventId, action
        if eventId ~= nil then
            g_inputBinding:setActionEventTextPriority(eventId, GS_PRIO_VERY_HIGH)
        end
    end
    if self.openEventId ~= nil then
        local text = g_i18n:getText("sdt_tablet_open")
        if kind == "tablet" then
            local x, _, z = getPlayerPosition()
            if x == nil or #SprayDroneLink.findTrailers(x, z, g_currentMission:getFarmId()) == 0 then
                text = g_i18n:getText("sdt_tablet_noConnection")
            end
        end
        g_inputBinding:setActionEventText(self.openEventId, text)
    end
end

function SprayDroneLink.removeOpenAction(self)
    if self.openEventId ~= nil and g_inputBinding ~= nil then
        g_inputBinding:beginActionEventsModification(PlayerInputComponent.INPUT_CONTEXT_NAME)
        g_inputBinding:removeActionEventsByTarget(self)
        g_inputBinding:endActionEventsModification()
    end
    self.openEventId, self.openAction = nil, nil
end

---------------------------------------------------------------------------------------------------
-- načtení a odebrání aktivace s mapou

function SprayDroneLink:loadMap()
    -- pojistka tyče: jednou do každé (i znovu načtené) tabulky SprayDroneRelay
    if SprayDroneRelay ~= nil and SprayDroneRelay.registerBlockCheck ~= nil and SprayDroneLink.blockCheckOwner ~= SprayDroneRelay then
        SprayDroneRelay.registerBlockCheck(SprayDroneLink.getRelayBlockReason)
        SprayDroneLink.blockCheckOwner = SprayDroneRelay
    end
end

function SprayDroneLink:deleteMap()
    SprayDroneLink.removeOpenAction(self)
end

addModEventListener(SprayDroneLink)
