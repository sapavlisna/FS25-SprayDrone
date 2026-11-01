-- Vlastní záložka obchodu „BZUK“ s kategoriemi z modDesc (storeCategories).
--
-- Hra <storeType>/<storeCategory> z modDesc sama nenačte (v logu pak „Invalid category … Using 'misc'“); mody s vlastní záložkou
-- (LSFM, Fendt F255GT Pack) je registrují po StoreManager.loadMapData stejně jako tady – nejdřív typ (záložka), pak kategorie.

SprayDroneStoreCategories = {}

SprayDroneStoreCategories.modDirectory = g_currentModDirectory
SprayDroneStoreCategories.modName = g_currentModName

function SprayDroneStoreCategories.loadMapData(storeManager, superFunc, ...)
    local result = superFunc(storeManager, ...)

    local xmlFile = XMLFile.load("sdtModDesc", SprayDroneStoreCategories.modDirectory .. "modDesc.xml")
    if xmlFile ~= nil then
        for _, key in xmlFile:iterator("modDesc.storeCategories.storeType") do
            storeManager:loadCategoryType(xmlFile, key, nil)
        end
        for _, key in xmlFile:iterator("modDesc.storeCategories.storeCategory") do
            storeManager:loadCategoryFromXML(xmlFile, key, SprayDroneStoreCategories.modDirectory, SprayDroneStoreCategories.modName)
        end
        xmlFile:delete()
    end

    return result
end

StoreManager.loadMapData = Utils.overwrittenFunction(StoreManager.loadMapData, SprayDroneStoreCategories.loadMapData)

-- Pořadí vleků v obchodě: ShopController.displayItemSortFunction řadí položky se stejným orderValue (= orderId kategorie)
-- od NEJDRAŽŠÍ (sellPrice2 < sellPrice1), pak podle xmlFilename - pořadí v modDesc ani storeData na to nemá vliv.
-- Naše vleky (kategorie sprayDroneTrailers, položky obchodu bez konkrétního vozidla) jdou proto od nejlevnějšího
-- (Mini, Middle, Max) a ve smíšeném seznamu před ostatní; zbytek obchodu se řadí beze změny.
SprayDroneStoreCategories.TRAILER_CATEGORY = "SPRAYDRONETRAILERS"

function SprayDroneStoreCategories.isOwnTrailer(item)
    local storeItem = item ~= nil and item.storeItem
    if storeItem == nil or storeItem.customEnvironment ~= SprayDroneStoreCategories.modName or item.saleItem ~= nil
        or (item.concreteItem ~= nil and item.concreteItem ~= ShopDisplayItem.NO_CONCRETE_ITEM) then
        return false
    end
    for _, name in ipairs(storeItem.categoryNames or { storeItem.categoryName }) do
        if name ~= nil and string.upper(name) == SprayDroneStoreCategories.TRAILER_CATEGORY then
            return true
        end
    end
    return false
end

function SprayDroneStoreCategories.displayItemSortFunction(superFunc, item1, item2)
    if item1.orderValue == item2.orderValue then
        local own1, own2 = SprayDroneStoreCategories.isOwnTrailer(item1), SprayDroneStoreCategories.isOwnTrailer(item2)
        if own1 and own2 then
            local p1, p2 = item1.storeItem.price or 0, item2.storeItem.price or 0
            if p1 ~= p2 then
                return p1 < p2
            end
            return item1.storeItem.xmlFilename < item2.storeItem.xmlFilename
        elseif own1 ~= own2 then
            return own1
        end
    end
    return superFunc(item1, item2)
end

if ShopController ~= nil and ShopController.displayItemSortFunction ~= nil and ShopDisplayItem ~= nil then
    local superSort = ShopController.displayItemSortFunction
    ShopController.displayItemSortFunction = function(item1, item2)
        return SprayDroneStoreCategories.displayItemSortFunction(superSort, item1, item2)
    end
else
    Logging.warning("SprayDrone: ShopController.displayItemSortFunction nenalezena, vleky v obchodě zůstanou v pořadí hry")
end
