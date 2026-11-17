-- Spojení s dronem: přenosná relé tyč a mobilní vysílačka (tablet).
--
-- Dosah dronu je dosah rádia vleku (sprayDrone#maxRange, s anténou z konfigurace vyšší). Relé tyč (SprayDroneRelay.lua, rozložená,
-- zapnutá, stojí vzpřímená a nikdo ji nedrží) ho prodlouží, když sama stojí v rádiu vleku. Tyče jsou dvě (RELAY_FILES):
-- všesměrová (objects/relay/relayPole.xml) pokrývá kruh o svém poloměru, směrová (objects/relay/relayPoleDirectional.xml,
-- sprayDroneRelay#sectorAngle / #sectorFactor) jen výseč ve směru čela panelu (osa +Z tyče) s dosahem násobku poloměru a jinde nic.
-- Oblast tyče {x, z, r, sectors} dává getRelayShape (r = 0 u směrové), bod v ní isInShape.
-- Tablet (objects/tablet/droneTablet.xml, ruční nástroj jako baterka) drží
-- hráč v ruce a levým tlačítkem (ACTIVATE_HANDTOOL, jako vanilla ruční nástroje) jím otevře plánovač vleku nebo kufru s dronem, který je ve spojení; jinak je vidět
-- NO CONNECTION. Cílů může být víc: výchozí je naposled použitý, v plánovači se přepíná PageUp / PageDown (openTablet(step)).
-- Totéž přepínání má plánovač otevřený ve vleku (Alt+7) nebo z displeje; cíle se tam berou z domova toho vleku (getStationTargets).
-- Kufr (profil portable) nemá anténu jako konfiguraci ani centrálu: spojení s ním je jeho sprayDrone#maxRange (sken 500 m, AIRASI 400 m), relé jako
-- u vleku.
-- Hráč je ve spojení, když je v dosahu rádia vleku, nebo aktivního relé, které je s vlekem spojené.
-- Na vleku je pevný displej (i3dMapping plannerScreenNode, osa +Z ven z obrazovky): pěší hráč u něj otevře plánovač (levé tlačítko myši, ACTIVATE_HANDTOOL),
-- plánovač se zavře, když od displeje odejde nebo se vlek složí.
--
-- Pojistky signálu: dávka, jejíž trasa vede mimo rádio vleku, závisí na tyčích (getNeededRelays); před odletem musí mít
-- každá výdrž na dávku s rezervou (getRelayRequiredSeconds), tyč, na které závisí letící dron, nejde složit ani vypnout
-- (getRelayBlockReason, registruje se do SprayDroneRelay.registerBlockCheck).

SprayDroneLink = {}

SprayDroneLink.RELAY_FILES = { "relayPole.xml", "relayPoleDirectional.xml" }
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

local function distance2D(ax, az, bx, bz)
    return math.sqrt((ax - bx) ^ 2 + (az - bz) ^ 2)
end

local TWO_PI = 2 * math.pi
local EPS = 1e-6

-- Úhel do (-pi, pi>.
local function normalizeAngle(a)
    return math.pi - (math.pi - a) % TWO_PI
end

-- Je vozidlo relé tyč (všesměrová i směrová, podle konce názvu souboru)?
function SprayDroneLink.isRelayPole(vehicle)
    for _, file in ipairs(SprayDroneLink.RELAY_FILES) do
        if hasFile(vehicle, file) then
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

-- Výseč směrové tyče {angle = plný úhel (rad), factor = násobek poloměru}, nil u všesměrové.
function SprayDroneLink.getRelaySector(vehicle)
    local relaySpec = SprayDroneRelay ~= nil and vehicle[SprayDroneRelay.SPEC_NAME] or nil
    return relaySpec ~= nil and relaySpec.sector or nil
end

-- Směr čela tyče (rad, atan2(dz, dx) osy +Z předmětu ve vodorovné rovině).
function SprayDroneLink.getRelayDirection(vehicle)
    local dx, _, dz = localDirectionToWorld(vehicle.rootNode, 0, 0, 1)
    return math.atan2(dz, dx)
end

-- Oblast signálu tyče (čistá funkce): všesměrová kruh o poloměru radius; směrová (sector) jen výseč o plném úhlu sector.angle
-- kolem směru dir s dosahem radius × sector.factor, kruh r = 0. Vrací {x, z, r, radius, sectors = {{dir, half, r}}}.
function SprayDroneLink.getRelayShape(x, z, radius, sector, dir)
    if sector == nil then
        return { x = x, z = z, r = radius, radius = radius, sectors = {} }
    end
    return { x = x, z = z, r = 0, radius = radius,
        sectors = { { dir = normalizeAngle(dir or 0), half = sector.angle * 0.5, r = radius * sector.factor } } }
end

-- Oblast tyče ve hře (getRelayShape z polohy, síly, výseče a natočení) s vozidlem.
function SprayDroneLink.getRelayEntry(vehicle)
    local x, _, z = getWorldTranslation(vehicle.rootNode)
    local sector = SprayDroneLink.getRelaySector(vehicle)
    local entry = SprayDroneLink.getRelayShape(x, z, SprayDroneLink.getRelayRadius(vehicle), sector,
        sector ~= nil and SprayDroneLink.getRelayDirection(vehicle) or nil)
    entry.vehicle = vehicle
    return entry
end

function SprayDroneLink.getActiveRelays()
    local held = getHeldNodes()
    local relays = {}
    for _, vehicle in ipairs(getVehicles()) do
        if SprayDroneLink.isRelayPole(vehicle) and SprayDroneLink.isRelayActive(vehicle, held) then
            table.insert(relays, SprayDroneLink.getRelayEntry(vehicle))
        end
    end
    return relays
end

-- Všechny tyče na mapě (i složené a vypnuté) pro ikony v plánovači: oblast (getRelayEntry) a jestli je aktivní.
function SprayDroneLink.getRelays()
    local held = getHeldNodes()
    local relays = {}
    for _, vehicle in ipairs(getVehicles()) do
        if SprayDroneLink.isRelayPole(vehicle) and not vehicle.isDeleted and vehicle.rootNode ~= nil and entityExists(vehicle.rootNode) then
            local entry = SprayDroneLink.getRelayEntry(vehicle)
            entry.active = SprayDroneLink.isRelayActive(vehicle, held)
            table.insert(relays, entry)
        end
    end
    return relays
end

---------------------------------------------------------------------------------------------------
-- oblast signálu: kruh a výseče (rádio stanice, tyče; čisté funkce, tools/test_relay_sector.py)

-- Dosah oblasti (m) ve směru bodu (x, z) od jejího středu. margin (m) rozšíří výseč i o úhel, který na té vzdálenosti dělá margin.
function SprayDroneLink.getShapeRange(shape, x, z, margin)
    local r = shape.r or shape.radius
    local sectors = shape.sectors
    if sectors ~= nil and #sectors > 0 then
        local d = distance2D(shape.x, shape.z, x, z)
        if d > EPS then
            local a = math.atan2(z - shape.z, x - shape.x)
            local slack = (margin or 0) / math.max(d, 1)
            for _, s in ipairs(sectors) do
                if s.r > r and math.abs(normalizeAngle(a - s.dir)) <= s.half + slack + EPS then
                    r = s.r
                end
            end
        end
    end
    return r
end

-- Nejdelší dosah oblasti (m) v jakémkoli směru.
function SprayDroneLink.getShapeMaxRange(shape)
    local r = shape.r
    for _, s in ipairs(shape.sectors or {}) do
        r = math.max(r, s.r)
    end
    return r
end

-- Leží bod (x, z) v oblasti rádia? margin (m) ji zvětší.
function SprayDroneLink.isInShape(shape, x, z, margin)
    margin = margin or 0
    return distance2D(shape.x, shape.z, x, z) <= SprayDroneLink.getShapeRange(shape, x, z, margin) + margin
end

-- Části úseků legs ({x1, z1, x2, z2}), kde inside(x, z) neplatí (podle středů kroků po step m): {x1, z1, x2, z2}.
function SprayDroneLink.getOutsideParts(legs, inside, step)
    step = step or 5
    local parts = {}
    for _, leg in ipairs(legs) do
        local len = distance2D(leg.x1, leg.z1, leg.x2, leg.z2)
        local n = math.max(1, math.ceil(len / step))
        local from = nil
        for i = 0, n do
            local out = false
            if i < n then
                local t = (i + 0.5) / n
                out = not inside(leg.x1 + (leg.x2 - leg.x1) * t, leg.z1 + (leg.z2 - leg.z1) * t)
            end
            if out and from == nil then
                from = i
            elseif not out and from ~= nil then
                local t1, t2 = from / n, i / n
                table.insert(parts, { x1 = leg.x1 + (leg.x2 - leg.x1) * t1, z1 = leg.z1 + (leg.z2 - leg.z1) * t1,
                    x2 = leg.x1 + (leg.x2 - leg.x1) * t2, z2 = leg.z1 + (leg.z2 - leg.z1) * t2 })
                from = nil
            end
        end
    end
    return parts
end

-- Obrys sjednocení kruhů {x, z, r}: úsečky {x1, z1, x2, z2, circle = index kruhu}, jen z úseků, které neleží uvnitř jiného
-- kruhu. Kruh se rozdělí v průsečících s ostatními na oblouky, oblouk se bere podle svého středu; plný kruh má `segments` úseček.
-- Shodné kruhy se kreslí jen jednou (ten s nižším indexem). Kruh s výsečemi se dělí i na hranách výsečí; kruh r = 0 (směrová tyč)
-- se nekreslí, jen jeho výseč (getCoverageLines).
function SprayDroneLink.getCoverageArcs(circles, segments)
    segments = segments or 96
    local lines = {}
    for i, c in ipairs(circles) do
        local hidden = c.r <= 0
        local cuts = { 0, TWO_PI }
        for _, s in ipairs(c.sectors or {}) do
            table.insert(cuts, (s.dir - s.half) % TWO_PI)
            table.insert(cuts, (s.dir + s.half) % TWO_PI)
        end
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

-- Obrys signálu: getCoverageArcs a k tomu výseče kruhů (circles[i].sectors): oblouk výseče a boky od kruhu ven. Úseky uvnitř jiné
-- výseče nebo kruhu se vynechají. Úsečky nesou circle = index kruhu, ke kterému výseč patří, a sector = true.
function SprayDroneLink.getCoverageLines(circles, segments)
    segments = segments or 96
    local sectors = {}
    for i, c in ipairs(circles) do
        for _, s in ipairs(c.sectors or {}) do
            table.insert(sectors, { x = c.x, z = c.z, dir = s.dir, half = s.half, r = s.r, r0 = c.r, circle = i })
        end
    end
    local lines = SprayDroneLink.getCoverageArcs(circles, segments)
    if #sectors == 0 then
        return lines
    end
    local function insideSector(x, z, skip)
        for k, s in ipairs(sectors) do
            local d = distance2D(s.x, s.z, x, z)
            if k ~= skip and d > EPS and d < s.r - EPS
                and math.abs(normalizeAngle(math.atan2(z - s.z, x - s.x) - s.dir)) < s.half - EPS then
                return true
            end
        end
        return false
    end
    local function insideCircle(x, z)
        for _, c in ipairs(circles) do
            if distance2D(c.x, c.z, x, z) < c.r - EPS then
                return true
            end
        end
        return false
    end
    local result = {}
    for _, line in ipairs(lines) do
        if not insideSector((line.x1 + line.x2) * 0.5, (line.z1 + line.z2) * 0.5) then
            table.insert(result, line)
        end
    end
    for k, s in ipairs(sectors) do
        local function add(x1, z1, x2, z2)
            local mx, mz = (x1 + x2) * 0.5, (z1 + z2) * 0.5
            if not insideCircle(mx, mz) and not insideSector(mx, mz, k) then
                table.insert(result, { x1 = x1, z1 = z1, x2 = x2, z2 = z2, circle = s.circle, sector = true })
            end
        end
        local n = math.max(1, math.ceil(segments * 2 * s.half / TWO_PI))
        local a0 = s.dir - s.half
        for j = 0, n - 1 do
            local b1, b2 = a0 + 2 * s.half * j / n, a0 + 2 * s.half * (j + 1) / n
            add(s.x + math.cos(b1) * s.r, s.z + math.sin(b1) * s.r, s.x + math.cos(b2) * s.r, s.z + math.sin(b2) * s.r)
        end
        local steps = 8
        for _, a in ipairs({ s.dir - s.half, s.dir + s.half }) do
            local ca, sa = math.cos(a), math.sin(a)
            for j = 0, steps - 1 do
                local r1, r2 = s.r0 + (s.r - s.r0) * j / steps, s.r0 + (s.r - s.r0) * (j + 1) / steps
                add(s.x + ca * r1, s.z + sa * r1, s.x + ca * r2, s.z + sa * r2)
            end
        end
    end
    return result
end

-- Azimut pro hráče (stupně od severu = -Z mapy, po směru hodin) ze směru dir (rad, atan2(dz, dx)).
function SprayDroneLink.getAzimuth(dir)
    return (math.deg(math.atan2(math.cos(dir), -math.sin(dir)))) % 360
end

-- Oblast rádia stanice: kruh spec.maxRange (u vleku už s anténou z konfigurace v obchodě) se středem v domově dronu.
function SprayDroneLink.getRadio(vehicle)
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    local hx, hz = SprayDroneStation.getHomePosition(vehicle)
    return { x = hx, z = hz, r = spec.maxRange, sectors = {} }
end

-- Kruhy signálu vleku pro obrys: rádio vleku (index 1) a oblast každé aktivní tyče, která je s vlekem spojená (jako isConnected);
-- u směrové tyče jen výseč (r = 0).
function SprayDroneLink.getSignalCircles(vehicle)
    local radio = SprayDroneLink.getRadio(vehicle)
    local circles = { radio }
    for _, relay in ipairs(SprayDroneLink.getActiveRelays()) do
        if SprayDroneLink.isInShape(radio, relay.x, relay.z) then
            table.insert(circles, { x = relay.x, z = relay.z, r = relay.r, sectors = relay.sectors })
        end
    end
    return circles
end

-- O kolik metrů relé prodlužují dosah vleku (strop dosahu z baterie: rádio + bonus): vzdálenost nejvzdálenějšího aktivního relé
-- v dosahu rádia vleku (`radio`: poloměr v m, nebo oblast getRadio); sahá-li tyč dál než rádio (směrová), i o ten rozdíl.
function SprayDroneLink.getRangeBonus(vehicle, radio)
    local hx, hz = SprayDroneStation.getHomePosition(vehicle)
    local radioMax = type(radio) == "table" and SprayDroneLink.getShapeMaxRange(radio) or radio
    local bonus = 0
    for _, relay in ipairs(SprayDroneLink.getActiveRelays()) do
        local d = distance2D(hx, hz, relay.x, relay.z)
        local inside = type(radio) == "table" and SprayDroneLink.isInShape(radio, relay.x, relay.z) or (type(radio) ~= "table" and d <= radio)
        if inside then
            bonus = math.max(bonus, d, d + SprayDroneLink.getShapeMaxRange(relay) - radioMax)
        end
    end
    return bonus
end

-- Je bod (x, z) ve spojení s vlekem? Rádio vleku, nebo oblast aktivního relé spojeného s vlekem.
function SprayDroneLink.isConnected(vehicle, x, z)
    local radio = SprayDroneLink.getRadio(vehicle)
    if SprayDroneLink.isInShape(radio, x, z) then
        return true
    end
    for _, relay in ipairs(SprayDroneLink.getActiveRelays()) do
        if SprayDroneLink.isInShape(radio, relay.x, relay.z) and SprayDroneLink.isInShape(relay, x, z) then
            return true
        end
    end
    return false
end

---------------------------------------------------------------------------------------------------
-- pojistky signálu (čisté funkce: tmp/f/test_signal.lua)

-- Leží bod (x, z) v některém z kruhů {x, z, r} (s výsečemi = oblast getRadio / getRelayShape)? margin (m) kruhy zvětší.
function SprayDroneLink.isInCircles(circles, x, z, margin)
    margin = margin or 0
    for _, c in ipairs(circles) do
        if c.sectors ~= nil then
            if SprayDroneLink.isInShape(c, x, z, margin) then
                return true
            end
        elseif distance2D(c.x, c.z, x, z) <= c.r + margin then
            return true
        end
    end
    return false
end

-- Tyče, na kterých dávka závisí: ty z relays (oblasti getRelayShape s vozidlem, nebo {x, z, radius}; spojené s vlekem), v jejichž
-- oblasti leží některý bod trasy (points {x, z}; body bez x se přeskočí) mimo rádio vleku (střed hx, hz, poloměr radio, nebo
-- radio = oblast getRadio).
-- Bod pokrytý víc tyčemi zaváže všechny.
function SprayDroneLink.getNeededRelays(points, hx, hz, radio, relays)
    local needed, used = {}, {}
    local function outside(x, z)
        if type(radio) == "table" then
            return not SprayDroneLink.isInShape(radio, x, z)
        end
        return distance2D(hx, hz, x, z) > radio
    end
    for _, p in ipairs(points) do
        if p.x ~= nil and p.z ~= nil and outside(p.x, p.z) then
            for i, relay in ipairs(relays) do
                if not used[i] and SprayDroneLink.isInShape(relay, p.x, p.z) then
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

-- Potřebuje tyč relay (oblast getRelayShape s vozidlem) některý dron? drones = { {relays = vozidla tyčí, na kterých závisí jeho dávka,
-- x, z = poloha dronu ve vzduchu (nil na vleku), others = kruhy signálu jeho vleku bez této tyče (rádio vleku a ostatní tyče)} }.
-- Ano, když na ní závisí jeho dávka, nebo je dron v její oblasti a jinde signál nemá.
function SprayDroneLink.isRelayNeeded(relay, drones)
    for _, d in ipairs(drones) do
        for _, used in ipairs(d.relays or {}) do
            if used == relay.vehicle then
                return true
            end
        end
        if d.x ~= nil and SprayDroneLink.isInShape(relay, d.x, d.z) and not SprayDroneLink.isInCircles(d.others or {}, d.x, d.z) then
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

-- Cíl tabletu (čisté funkce, tools/test_tablet.py): entries = findTrailers (seřazené rankTrailers). Výchozí je naposled použitý
-- cíl (last), je-li ve spojení, jinak první (puštěná mise, rozložený, nejbližší). Vrací index, nil = žádný cíl.
function SprayDroneLink.pickTarget(entries, last)
    for i, e in ipairs(entries) do
        if e.vehicle == last then
            return i
        end
    end
    return #entries > 0 and 1 or nil
end

-- Index cíle o step (+1 / -1) dál od vozidla current, dokola; current mimo seznam = výchozí podle pickTarget.
function SprayDroneLink.cycleTarget(entries, current, step)
    local n = #entries
    for i, e in ipairs(entries) do
        if e.vehicle == current then
            return (i - 1 + step) % n + 1
        end
    end
    return SprayDroneLink.pickTarget(entries, nil)
end

-- Vozidlo, které tablet místního hráče naposled ovládal (jen klient a jen v paměti; příkazy jdou eventy na konkrétní vozidlo).
SprayDroneLink.tabletTarget = nil

-- Cíle tabletu z polohy místního hráče: vleky a kufry farmy s dronem ve spojení, seřazené.
function SprayDroneLink.getTabletTargets()
    local x, _, z = getPlayerPosition()
    if x == nil or g_currentMission == nil then
        return {}
    end
    return SprayDroneLink.findTrailers(x, z, g_currentMission:getFarmId())
end

-- Cíle plánovače otevřeného na vleku (Alt+7 ve vleku, displej): pravidlo jako u tabletu, jen místo polohy hráče platí domov vleku,
-- ze kterého se plánovač otevřel (origin) - vleky a kufry farmy s dronem ve spojení s ním. Origin je v seznamu vždy (i bez dronu),
-- aby se na něj šlo vrátit.
function SprayDroneLink.getStationTargets(origin, farmId)
    local x, z = SprayDroneStation.getHomePosition(origin)
    local result = {}
    for _, e in ipairs(SprayDroneLink.collectTrailers(x, z, farmId)) do
        if e.inRange or e.vehicle == origin then
            table.insert(result, e)
        end
    end
    return result
end

-- Smí plánovač otevřený na vleku origin dál ovládat vehicle? Sám sebe vždy, jiný vlek / kufr jen s dronem a ve spojení s originem.
function SprayDroneLink.isStationTargetConnected(origin, vehicle)
    if vehicle == origin then
        return true
    end
    local x, z = SprayDroneStation.getHomePosition(origin)
    return vehicle[SprayDroneStation.SPEC_NAME].hasDrone == true and SprayDroneLink.isConnected(vehicle, x, z)
end

-- Cíle přepínání v plánovači podle režimu otevření: tablet z polohy hráče, jinak z vleku origin.
function SprayDroneLink.getPlannerTargets(mode, origin)
    if mode == SprayDronePlannerScreen.MODE_TABLET or origin == nil then
        return SprayDroneLink.getTabletTargets()
    end
    return SprayDroneLink.getStationTargets(origin, g_currentMission:getFarmId())
end

-- Popis cíle pro hráče: jméno vozidla (obchod), vzdálenost a stav (letí / rozloženo / složeno).
function SprayDroneLink.getTargetLabel(entry)
    local vehicle = entry.vehicle
    local name = vehicle.getName ~= nil and vehicle:getName() or nil
    if name == nil or name == "" then
        name = tostring(vehicle.configFileName)
    end
    local state = entry.missionActive and "sdt_tablet_stateMission" or (entry.unfolded and "sdt_tablet_stateUnfolded" or "sdt_tablet_stateFolded")
    return string.format(g_i18n:getText("sdt_tablet_target"), name, entry.distance, g_i18n:getText(state))
end

-- Proč by tablet teď nic neotevřel (klíč textu / popis pro ladění), nil = otevře.
function SprayDroneLink.getTabletBlocker()
    if g_localPlayer == nil then
        return "bez místního hráče"
    end
    if SprayDroneLink.getHeldTablet() == nil then
        return "hráč nedrží tablet"
    end
    if g_gui ~= nil and g_gui:getIsGuiVisible() then
        return "je otevřené GUI"
    end
    if g_localPlayer.getCurrentVehicle ~= nil and g_localPlayer:getCurrentVehicle() ~= nil then
        return "hráč sedí ve vozidle"
    end
    if #SprayDroneLink.getTabletTargets() == 0 then
        return "žádný vlek ani kufr s dronem ve spojení (NO CONNECTION)"
    end
    return nil
end

-- Otevře plánovač tabletem: bez step výchozí cíl (pickTarget), se step o tolik dál od cíle otevřeného plánovače (nebo naposled
-- použitého), s vehicle přímo ten cíl (klik na ikonu v mapě plánovače). Vrací otevřené vozidlo, nebo nil (bez spojení).
function SprayDroneLink.openTablet(step, vehicle)
    local found = SprayDroneLink.getTabletTargets()
    if #found == 0 then
        g_currentMission:showBlinkingWarning(g_i18n:getText("sdt_tablet_noConnection"), 2500)
        return nil
    end
    local index
    if vehicle ~= nil then
        index = SprayDroneLink.pickTarget(found, vehicle)
    elseif step ~= nil then
        local screen = SprayDronePlannerScreen.INSTANCE
        local current = screen ~= nil and screen:getIsOpen() and screen.vehicle or SprayDroneLink.tabletTarget
        index = SprayDroneLink.cycleTarget(found, current, step)
    else
        index = SprayDroneLink.pickTarget(found, SprayDroneLink.tabletTarget)
    end
    local entry = found[index]
    SprayDroneLink.tabletTarget = entry.vehicle
    local tool = SprayDroneLink.getHeldTablet()
    if tool ~= nil then
        tool.sdtScreenWake = g_time
    end
    SprayDroneSound.noteAction(string.format("tablet: cíl %d / %d %s (id %s)", index, #found, tostring(entry.vehicle.configFileName), tostring(entry.vehicle.id)))
    SprayDronePlannerScreen.show(entry.vehicle, SprayDronePlannerScreen.MODE_TABLET)
    return entry.vehicle
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
    local radio = SprayDroneLink.getRadio(vehicle)
    local relays = {}
    for _, relay in ipairs(SprayDroneLink.getActiveRelays()) do
        if SprayDroneLink.isInShape(radio, relay.x, relay.z) then
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
    if not SprayDroneLink.isRelayPole(relayVehicle) then
        return nil
    end
    local relay = SprayDroneLink.getRelayEntry(relayVehicle)
    local x, z = relay.x, relay.z
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
    -- i vlek bez dronu (jako Alt+7): plánovač pak přepne na jiný vlek / kufr ve spojení
    local spec = SprayDroneDrones.getRoot(vehicle)
    if spec == nil or spec.plannerScreenNode == nil
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

-- Kterému vleku teď patří otevřený plánovač a ze kterého se otevřel (nebo nil).
local function getPlannerVehicle()
    local screen = SprayDronePlannerScreen ~= nil and SprayDronePlannerScreen.INSTANCE or nil
    if screen ~= nil and screen.getIsOpen ~= nil and screen:getIsOpen() then
        return screen.vehicle, screen.originVehicle
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
    local plannerVehicle, plannerOrigin = getPlannerVehicle()
    for _, vehicle in ipairs(getVehicles()) do
        local spec = vehicle[SprayDroneStation.SPEC_NAME]
        if spec ~= nil and spec.plannerScreenOn ~= nil then
            if plannerVehicle == vehicle or plannerOrigin == vehicle then
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
-- ovládání pěšky (vlastní akce v kontextu hráče, ne ActivatableObjectsSystem – ten nabízí jen jednu nejbližší aktivaci a na Mini
-- by displej přebil bednu na R):
--  * levé tlačítko = ACTIVATE_HANDTOOL (vanilla „použít ruční nástroj“ a zvedání rukama; INTERACT na stejném tlačítku zvedání
--    přebíjí): tablet v ruce, displej vleku;
--  * B = SDT_TOGGLE_FOOT (zapnout / vypnout stroj): elektrocentrála vleku.
-- O tutéž klávesu se nedělí s vybranou aktivací modu (bedna, mlýnek, hadice, pumpa, tyč, kufr; hlásí se setSelected): vyhrává bližší
-- a druhá akci nepřijme ani neukáže (mayClick / mayToggle). Kliky navíc ustupují zvedání předmětu, na který hráč míří.

SprayDroneLink.GENERATOR_NODES = { "generatorExhaust", "generatorExhaust2" }
SprayDroneLink.GENERATOR_DISTANCE = 1.6    -- m vodorovně od výfuku centrály
SprayDroneLink.GENERATOR_BELOW = 2.5       -- hráč smí stát až tolik pod výfukem (na zemi vedle vleku)
SprayDroneLink.AIM_RADIUS = 0.35           -- hráč míří na uzel: kolmá vzdálenost uzlu od osy pohledu (m)
SprayDroneLink.AIM_RANGE = 4               -- … a uzel je nejvýš tak daleko před kamerou (m)
SprayDroneLink.AIM_BONUS = 1.5             -- aktivace, na jejíž uzel hráč míří, se pro výběr počítá o tolik m blíž

-- Míří místní hráč (osa aktivní kamery) na uzel?
function SprayDroneLink.isAimedAt(node, radius)
    if node == nil or node == 0 or not entityExists(node) or g_cameraManager == nil then
        return false
    end
    local camera = g_cameraManager:getActiveCamera()
    if camera == nil or camera == 0 then
        return false
    end
    local cx, cy, cz = getWorldTranslation(camera)
    local dx, dy, dz = localDirectionToWorld(camera, 0, 0, -1)
    local nx, ny, nz = getWorldTranslation(node)
    local vx, vy, vz = nx - cx, ny - cy, nz - cz
    local along = vx * dx + vy * dy + vz * dz
    if along <= 0 or along > SprayDroneLink.AIM_RANGE then
        return false
    end
    return MathUtil.vector3Length(vx - dx * along, vy - dy * along, vz - dz * along) <= (radius or SprayDroneLink.AIM_RADIUS)
end

-- Vzdálenost aktivace pro výběr ActivatableObjectsSystem: o AIM_BONUS menší, když hráč míří na její uzel (R dostane to, na co hráč
-- míří, a ne to, co je o pár decimetrů blíž).
function SprayDroneLink.aimDistance(distance, node)
    if distance ~= nil and distance < math.huge and SprayDroneLink.isAimedAt(node) then
        return math.max(distance - SprayDroneLink.AIM_BONUS, 0)
    end
    return distance
end

-- Vybraná aktivace modu (volá její registerCustomInput / removeCustomInput); nese clickEventId (levé tlačítko) a toggleEventId (B).
SprayDroneLink.selected = nil

function SprayDroneLink.setSelected(activatable, selected)
    if selected then
        SprayDroneLink.selected = activatable
    elseif SprayDroneLink.selected == activatable then
        SprayDroneLink.selected = nil
    end
end

-- Je vybraná aktivace s akcí field ("clickEventId" / "toggleEventId") blíž než distance?
local function isSelectedCloser(field, distance)
    local act = SprayDroneLink.selected
    if act == nil or act[field] == nil or act.getDistance == nil or (act.vehicle ~= nil and act.vehicle.isDeleted) then
        return false
    end
    local x, y, z = getPlayerPosition()
    return x ~= nil and act:getDistance(x, y, z) <= distance
end

local function isInVehicle(player)
    return player.getCurrentVehicle ~= nil and player:getCurrentVehicle() ~= nil
end

-- Smí levé tlačítko pěšky ovládat objekt? Ne ve vozidle, s tabletem nebo předmětem v ruce, ani když hráč míří na předmět, který
-- jde zvednout (zvedání je táž akce). activatable = vybraná aktivace: ne, když klik patří bližšímu displeji vleku.
function SprayDroneLink.mayClick(activatable)
    local player = g_localPlayer
    if player == nil or isInVehicle(player) or SprayDroneLink.getHeldTablet() ~= nil then
        return false
    end
    if activatable ~= nil and SprayDroneLink.openKind == "screen" then
        return false
    end
    local hands = player.hands
    if hands ~= nil and hands.getIsHoldingItem ~= nil then
        if hands:getIsHoldingItem() then
            return false
        end
        local targeter = player.targeter
        if targeter ~= nil and HandToolHands ~= nil and hands:getCanPickUpNode(targeter:getClosestTargetedNodeFromType(HandToolHands)) then
            return false
        end
    end
    return true
end

-- Smí B pěšky ovládat vybranou aktivaci? Ne, když B patří bližší elektrocentrále vleku.
function SprayDroneLink.mayToggle(activatable)
    return SprayDroneLink.toggleVehicle == nil
end

-- B pěšky (SDT_TOGGLE_FOOT) pro target. disableConflictingBindings: cizí FS25_handTools drží v kontextu hráče natrvalo HANDTOOL_TAKE
-- na B se stejným příznakem, bez něj by se akce při kolizi nezaregistrovala a B by nic nedělalo. Vrací id akce, nebo nil (zaloguje se).
function SprayDroneLink.registerToggle(target, callback, text)
    local _, eventId = g_inputBinding:registerActionEvent(InputAction.SDT_TOGGLE_FOOT, target, callback, false, true, false, true, nil, true)
    if eventId == nil then
        if not SprayDroneLink.toggleFailLogged then
            SprayDroneLink.toggleFailLogged = true
            Logging.warning("SDT: akci SDT_TOGGLE_FOOT (B pěšky) se nepodařilo zaregistrovat (kolize s jinou akcí na stejné klávese?)")
        end
        return nil
    end
    g_inputBinding:setActionEventTextPriority(eventId, GS_PRIO_VERY_HIGH)
    g_inputBinding:setActionEventTextVisibility(eventId, true)
    if text ~= nil then
        g_inputBinding:setActionEventText(eventId, text)
    end
    return eventId
end

-- Levé tlačítko pěšky (ACTIVATE_HANDTOOL) pro target: stejná akce jako zvedání rukama, takže s ní nekoliduje. Vrací id akce, nebo nil.
function SprayDroneLink.registerClick(target, callback, text)
    local _, eventId = g_inputBinding:registerActionEvent(InputAction.ACTIVATE_HANDTOOL, target, callback, false, true, false, true)
    if eventId == nil then
        return nil
    end
    g_inputBinding:setActionEventTextPriority(eventId, GS_PRIO_VERY_HIGH)
    g_inputBinding:setActionEventTextVisibility(eventId, text ~= nil)
    if text ~= nil then
        g_inputBinding:setActionEventText(eventId, text)
    end
    return eventId
end

-- Co se teď dá ovládat levým tlačítkem: "tablet", nebo "screen" + vlek + vzdálenost; nil = nic.
function SprayDroneLink.getOpenTarget()
    local player = g_localPlayer
    if player == nil or g_gui:getIsGuiVisible() or isInVehicle(player) then
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
    return bestKind, bestVehicle, bestDistance
end

-- Stojí místní hráč u elektrocentrály vleku? Vrací vodorovnou vzdálenost od nejbližšího výfuku, nebo nil.
function SprayDroneLink.getGeneratorDistance(vehicle, x, y, z)
    local best = nil
    for _, name in ipairs(SprayDroneLink.GENERATOR_NODES) do
        local node = SprayDroneStation.getMappedNode(vehicle, name)
        if node ~= nil and entityExists(node) and getEffectiveVisibility(node) then
            local nx, ny, nz = getWorldTranslation(node)
            local d = distance2D(x, z, nx, nz)
            if d <= SprayDroneLink.GENERATOR_DISTANCE and y >= ny - SprayDroneLink.GENERATOR_BELOW and y <= ny + 1 and (best == nil or d < best) then
                best = d
            end
        end
    end
    return best
end

-- Elektrocentrála vleku, kterou teď B pěšky zapne / vypne, a vzdálenost od ní; nil = žádná.
function SprayDroneLink.getGeneratorTarget()
    local player = g_localPlayer
    if player == nil or g_gui:getIsGuiVisible() or isInVehicle(player) then
        return nil
    end
    local x, y, z = getPlayerPosition()
    if x == nil then
        return nil
    end
    local best, bestDistance = nil, math.huge
    for _, vehicle in ipairs(getVehicles()) do
        local spec = vehicle[SprayDroneStation.SPEC_NAME]
        if spec ~= nil and spec.dieselFillUnitIndex ~= nil and not vehicle.isDeleted
            and not (VehiclePropertyState ~= nil and vehicle.propertyState == VehiclePropertyState.SHOP_CONFIG)
            and g_currentMission.accessHandler:canFarmAccess(player.farmId, vehicle) then
            local d = SprayDroneLink.getGeneratorDistance(vehicle, x, y, z)
            if d ~= nil and d < bestDistance then
                best, bestDistance = vehicle, d
            end
        end
    end
    return best, bestDistance
end

function SprayDroneLink:onPlayerAction()
    if self.openKind == "screen" and not SprayDroneLink.mayClick(nil) then
        return
    end
    SprayDroneSound.noteAction("otevření plánovače letu: " .. tostring(self.openKind))
    if self.openKind == "tablet" then
        SprayDroneLink.openTablet()
    elseif self.openKind == "screen" and self.openVehicle ~= nil then
        SprayDroneDrones.getRoot(self.openVehicle).screenWakeTime = g_time
        SprayDronePlannerScreen.show(self.openVehicle, SprayDronePlannerScreen.MODE_SCREEN)
    end
end

SprayDroneLink.toggleTarget = {}

function SprayDroneLink.onGeneratorToggle()
    local vehicle = SprayDroneLink.toggleVehicle
    if vehicle == nil or vehicle.isDeleted then
        return
    end
    SprayDroneSound.noteAction(string.format("B pěšky u elektrocentrály: vlek %s (id %s)", vehicle.configFileNameClean or "?", tostring(vehicle.id)))
    vehicle:sprayDroneCommand(SprayDroneCommandEvent.SET_GENERATOR, SprayDroneDrones.getRoot(vehicle).generatorEnabled and 0 or 1)
end

function SprayDroneLink:update(dt)
    if g_client ~= nil then
        SprayDroneLink.updateScreens()
    end
    if g_inputBinding == nil or PlayerInputComponent == nil then
        return
    end
    local kind, vehicle, screenDistance = SprayDroneLink.getOpenTarget()
    if kind == "screen" and (not SprayDroneLink.mayClick(nil) or isSelectedCloser("clickEventId", screenDistance)) then
        kind, vehicle = nil, nil
    end
    self.openKind, self.openVehicle = kind, vehicle
    local generator, generatorDistance = SprayDroneLink.getGeneratorTarget()
    if generator ~= nil and isSelectedCloser("toggleEventId", generatorDistance) then
        generator = nil
    end
    self.toggleVehicle = generator
    SprayDroneLink.updateToggleAction(self)
    if self.openEventId ~= nil and kind == nil then
        SprayDroneLink.removeOpenAction(self)
    end
    if kind ~= nil and self.openEventId == nil and self.openFailedKind ~= kind then
        g_inputBinding:beginActionEventsModification(PlayerInputComponent.INPUT_CONTEXT_NAME)
        local eventId = SprayDroneLink.registerClick(self, self.onPlayerAction, nil)
        g_inputBinding:endActionEventsModification()
        self.openEventId, self.openAction = eventId, eventId ~= nil and "ACTIVATE_HANDTOOL" or nil
        if eventId ~= nil then
            g_inputBinding:setActionEventTextVisibility(eventId, true)
        else
            self.openFailedKind = kind
            Logging.warning("SDT: levé tlačítko (ACTIVATE_HANDTOOL) pro %s se nepodařilo zaregistrovat", tostring(kind))
        end
    end
    if kind == nil then
        self.openFailedKind = nil
    end
    if self.openEventId ~= nil then
        local text = g_i18n:getText("sdt_tablet_open")
        if kind == "tablet" then
            local found = SprayDroneLink.getTabletTargets()
            local index = SprayDroneLink.pickTarget(found, SprayDroneLink.tabletTarget)
            if index == nil then
                text = g_i18n:getText("sdt_tablet_noConnection")
            else
                text = string.format(g_i18n:getText("sdt_tablet_openTarget"), SprayDroneLink.getTargetLabel(found[index]))
            end
        end
        if text ~= self.openText then
            self.openText = text
            g_inputBinding:setActionEventText(self.openEventId, text)
        end
    end
end

function SprayDroneLink.removeOpenAction(self)
    if self.openEventId ~= nil and g_inputBinding ~= nil then
        g_inputBinding:beginActionEventsModification(PlayerInputComponent.INPUT_CONTEXT_NAME)
        g_inputBinding:removeActionEventsByTarget(self)
        g_inputBinding:endActionEventsModification()
    end
    self.openEventId, self.openAction, self.openText = nil, nil, nil
end

-- B pěšky u elektrocentrály: akce žije, dokud je hráč u centrály (toggleVehicle), text podle stavu centrály.
function SprayDroneLink.updateToggleAction(self)
    local target = SprayDroneLink.toggleTarget
    local vehicle = self.toggleVehicle
    if vehicle == nil then
        SprayDroneLink.removeToggleAction()
        return
    end
    if target.eventId == nil and not target.failed then
        g_inputBinding:beginActionEventsModification(PlayerInputComponent.INPUT_CONTEXT_NAME)
        target.eventId = SprayDroneLink.registerToggle(target, SprayDroneLink.onGeneratorToggle, nil)
        g_inputBinding:endActionEventsModification()
        target.text, target.failed = nil, target.eventId == nil
    end
    if target.eventId ~= nil then
        local text = g_i18n:getText(SprayDroneDrones.getRoot(vehicle).generatorEnabled and "sdt_action_generatorOff" or "sdt_action_generatorOn")
        if text ~= target.text then
            target.text = text
            g_inputBinding:setActionEventText(target.eventId, text)
        end
    end
end

function SprayDroneLink.removeToggleAction()
    local target = SprayDroneLink.toggleTarget
    if target.eventId ~= nil and g_inputBinding ~= nil then
        g_inputBinding:beginActionEventsModification(PlayerInputComponent.INPUT_CONTEXT_NAME)
        g_inputBinding:removeActionEventsByTarget(target)
        g_inputBinding:endActionEventsModification()
    end
    target.eventId, target.text, target.failed = nil, nil, nil
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
    SprayDroneLink.removeToggleAction()
    SprayDroneLink.selected, SprayDroneLink.toggleVehicle = nil, nil
end

addModEventListener(SprayDroneLink)
