-- Míchání přípravku z vody a koncentrátu (docs/DRON.md, „Koncentrát a mixér“). Čisté funkce bez závislosti na hře,
-- aby šly zkoušet mimo ni (tools: lupa). ratio r = litrů koncentrátu na litr hotového přípravku, zbytek (1 - r) je voda.
--
-- Příklad ručním výpočtem: r = 0,05 (hnojivo i herbicid), voda 300 l, koncentrát 20 l (jeden kanystr)
--   na 1 l přípravku 0,05 l koncentrátu + 0,95 l vody;  voda / 0,95 = 315,8 l, koncentrát / 0,05 = 400 l  =>  315,8 l
--   (omezuje voda; spotřeba 300 l vody + 15,8 l koncentrátu).

SprayDroneMixer = {}

SprayDroneMixer.MIN_RATIO = 0.01
SprayDroneMixer.MAX_RATIO = 0.99
SprayDroneMixer.EPSILON = 0.001

SprayDroneMixer.KIND_NONE = "none"
SprayDroneMixer.KIND_DIRECT = "direct"
SprayDroneMixer.KIND_MIX = "mix"

function SprayDroneMixer.clampRatio(ratio)
    return math.min(math.max(ratio, SprayDroneMixer.MIN_RATIO), SprayDroneMixer.MAX_RATIO)
end

-- Voda a koncentrát (l) na `liters` l přípravku.
function SprayDroneMixer.getParts(ratio, liters)
    ratio = SprayDroneMixer.clampRatio(ratio)
    return liters * (1 - ratio), liters * ratio
end

-- Kolik litrů přípravku jde namíchat ze zásob; druhý výsledek je omezující složka ("water" / "concentrate").
function SprayDroneMixer.getAvailable(ratio, water, concentrate)
    ratio = SprayDroneMixer.clampRatio(ratio)
    local fromWater = math.max(water, 0) / (1 - ratio)
    local fromConcentrate = math.max(concentrate, 0) / ratio
    if fromWater < fromConcentrate then
        return fromWater, "water"
    end
    return fromConcentrate, "concentrate"
end

-- Odkud dron dostane přípravek. mainType / mainLevel je hlavní nádrž vleku, concType / concLevel koncentrátová,
-- ratios[concType] = r pro druhy koncentrátů, products[concType] = druh hotového přípravku (vanilla herbicide / liquidFertilizer;
-- bez záznamu je přípravek stejného druhu jako koncentrát), waterType druh vody.
-- Výsledek: kind (direct / mix / none), fillType (druh přípravku pro dron, u none případně jen odhad nebo nil),
-- liters (kolik přípravku je k dispozici), ratio a concentrateType (u mix), reason (u none: "empty", "noWater", "noConcentrate").
function SprayDroneMixer.resolve(mainType, mainLevel, concType, concLevel, ratios, waterType, products)
    local eps = SprayDroneMixer.EPSILON
    local hasMain = mainType ~= nil and mainLevel > eps
    local hasConc = concType ~= nil and concLevel > eps and ratios[concType] ~= nil
    local product = concType ~= nil and products ~= nil and products[concType] or concType
    if hasMain and mainType ~= waterType then
        return { kind = SprayDroneMixer.KIND_DIRECT, fillType = mainType, liters = mainLevel }
    end
    if hasMain and hasConc then
        local ratio = SprayDroneMixer.clampRatio(ratios[concType])
        local liters, limit = SprayDroneMixer.getAvailable(ratio, mainLevel, concLevel)
        return { kind = SprayDroneMixer.KIND_MIX, fillType = product, liters = liters, ratio = ratio, limit = limit, concentrateType = concType }
    end
    local result = { kind = SprayDroneMixer.KIND_NONE, liters = 0, fillType = hasConc and product or nil }
    if hasMain then
        result.reason = "noConcentrate"
    elseif hasConc then
        result.reason = "noWater"
    else
        result.reason = "empty"
    end
    return result
end

-- Smí se dron vypustit do hlavní nádrže? Jen do prázdné, nebo s týmž přípravkem (vanilla by jiný druh při nízké
-- hladině potichu přepsala).
function SprayDroneMixer.canAcceptDrained(mainType, mainLevel, droneType)
    if droneType == nil or mainLevel <= SprayDroneMixer.EPSILON then
        return true
    end
    return mainType == droneType
end
