-- Dva drony na jednom vleku (docs/DVA_DRONY_NAVRH.md, kap. 1.3): dron 1 je přímo spec vozidla, dron 2 je pohled na spec, který
-- sdílená pole (SprayDroneFields.shared) čte a zapisuje do spec a ostatní drží sám. Funkce SprayDroneStation, které čtou
-- self[SPEC_NAME], se tak beze změny spustí pro libovolný dron: runAs na dobu volání dosadí pohled dronu místo spec.

SprayDroneDrones = {}

local function toSet(list)
    local set = {}
    for _, name in ipairs(list) do
        set[name] = true
    end
    return set
end

SprayDroneDrones.SHARED = toSet(SprayDroneFields.shared)
SprayDroneDrones.DRONE = toSet(SprayDroneFields.drone)

function SprayDroneDrones.createView(root, index)
    local shared, drone, warned = SprayDroneDrones.SHARED, SprayDroneDrones.DRONE, {}
    local view = { rootSpec = root, droneIndex = index }
    return setmetatable(view, {
        __index = function(_, key)
            if shared[key] then
                return root[key]
            end
            return nil
        end,
        __newindex = function(t, key, value)
            if shared[key] then
                root[key] = value
            else
                if not drone[key] and not warned[key] then
                    warned[key] = true
                    Logging.warning("SDT: spec.%s není klasifikováno (sdílené / dron)", tostring(key))
                end
                rawset(t, key, value)
            end
        end
    })
end

-- Kořenový spec vozidla (= dron 1), z libovolného kontextu.
function SprayDroneDrones.getRoot(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    return rawget(spec, "rootSpec") or spec
end

-- Vrátí jako self[SPEC_NAME] kořen. Volá se na začátku snímku (onUpdate): když chyba ve funkci pod runAs (dron 2) přerušila
-- volání dřív, než runAs kontext vrátil, nezůstane vozidlo natrvalo v pohledu dronu 2.
function SprayDroneDrones.restoreRoot(self)
    self[SprayDroneStation.SPEC_NAME] = SprayDroneDrones.getRoot(self)
end

-- Počet dronů na vozidle (1, když druhý chybí).
function SprayDroneDrones.getCount(self)
    local root = SprayDroneDrones.getRoot(self)
    return root.numDrones or 1
end

-- Spec dronu k (nil, když takový dron není).
function SprayDroneDrones.getSpec(self, k)
    local root = SprayDroneDrones.getRoot(self)
    return root.drones ~= nil and root.drones[k] or (k == 1 and root or nil)
end

-- Dosadí na dobu fn(self, ...) pohled dronu k jako self[SPEC_NAME] a vrátí první tři výsledky. Dron 1 je root, ten se nepřepíná.
function SprayDroneDrones.runAs(self, k, fn, ...)
    local name = SprayDroneStation.SPEC_NAME
    local current = self[name]
    local target = SprayDroneDrones.getSpec(self, k)
    if target == nil then
        return nil
    end
    if target == current then
        return fn(self, ...)
    end
    self[name] = target
    local a, b, c = fn(self, ...)
    self[name] = current
    return a, b, c
end

-- fn(self, ...) pro každý dron zvlášť v pořadí 1, 2.
function SprayDroneDrones.forEach(self, fn, ...)
    for k = 1, SprayDroneDrones.getCount(self) do
        SprayDroneDrones.runAs(self, k, fn, ...)
    end
end

local function callWithSpec(self, fn, k)
    return fn(self[SprayDroneStation.SPEC_NAME], k)
end

-- Jako forEach, jen fn dostane spec dronu a jeho číslo: fn(spec, k). self[SPEC_NAME] je přitom také spec dronu.
function SprayDroneDrones.forEachSpec(self, fn)
    for k = 1, SprayDroneDrones.getCount(self) do
        SprayDroneDrones.runAs(self, k, callWithSpec, fn, k)
    end
end

-- Je podmínka cond(spec dronu) splněná u některého dronu?
function SprayDroneDrones.any(self, cond)
    local root = SprayDroneDrones.getRoot(self)
    for k = 1, SprayDroneDrones.getCount(self) do
        if cond(root.drones[k]) then
            return true
        end
    end
    return false
end

-- Index dronu, jehož spec je v aktuálním kontextu.
function SprayDroneDrones.getIndex(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    return rawget(spec, "droneIndex") or 1
end
