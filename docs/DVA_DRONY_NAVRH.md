# Dva drony na jednom vleku: návrh

Technický podklad pro implementaci bez možnosti testu ve hře. Stav kódu: `mod/FS25_SprayDroneTrailer/scripts/*` z 2026-10-04 (Station 3472 řádků, Service 809, Route 2171, Pad 399, Toolbox 2142, Planner 861). Nic se tu nemění, jen se popisuje, co a kde změnit. Čísla řádků jsou ze zdrojů k tomuto datu; po každé etapě se posunou.

Model, ke kterému se návrh vztahuje, už vzniká: `blender/build_trailer_max.py`, `export_max_mod.py`, šablona `blender/templates/sprayDroneTrailerMax.xml.in`. Z nich jsem převzal tyto fakty (jsou závazné pro kontrakt v kap. 5):

- plochy: `PAD_Y = (TOP_Y0 + 1,10 ; TOP_Y1 − 1,10) = (−1,20 ; 3,05)` m, tedy **rozteč kořenů dronů 4,25 m**; dron A (přední, prefix `Drone_*`), dron B (zadní, prefix `Drone2_*`), oba nosem dopředu (`DRONE_YAW = 0`);
- `BATTERY_COUNT = 8` šachet nabíječky (`battery1..8`, `batterySlotDeck1..8`, `Charger_Led_<k>_<n>` pro k = 1..8, n = 0..3), jeden navíječ (`fillHoseCoil/Start/Lay1..5/Seg1..96/Nozzle/ParkPos`), jedna koncovka v parku uprostřed paluby;
- jeden `fillUnit` 1 pro obě nádrže za sebou (6 000 / 10 000 l), `fillUnit` 2 nafta 60 l, `fillUnit` 3 koncentrát 100 l;
- `export_max_mod.py` slučuje `DRONE_VARIANTS` s klíči `S2/M2/L2`, takže `clamp_parts_xml` už dává úchyty obou dronů a `values["DRONE_PARTS_S2|M2|L2"]` už existují, jen je šablona nepoužívá.

---

## 0. Shrnutí a doporučení

1. **Architektura: „dron 1 = stávající `spec`, dron 2 = pohled (view) na `spec`“ s přepínáním kontextu (`runAs`).** Každé vozidlo má `spec.drones = { [1] = spec, [2] = view2 }`. `view2` je prázdná tabulka s metatabulkou: pole z kapitoly 1.5 označená jako *sdílená* čte i zapisuje v `spec`, všechna ostatní (per-drone) drží sama. Stávající funkce se nepřepisují: `runAs(self, 2, fn, …)` na dobu volání dosadí `self[SPEC_NAME] = view2`, takže `local spec = self[SprayDroneStation.SPEC_NAME]` uvnitř `fn` vidí stav druhého dronu. Pro dron 1 se nic nepřepíná (`spec` je jeho tabulka), proto **jednodronové vleky (Car, Mini) po etapě 1 běží přesně týmž kódem jako dnes**.
2. **Oba drony mají tutéž variantu (S / M / L)** a tytéž parametry (`workWidth`, `tankCapacity`, rychlosti, baterie). To zruší ~50 polí ze seznamu „per-drone“ (zůstanou konstanty vozidla) a fond baterií je typově jednotný. Rozlišují se jen uzly, poloha, stav a trasa. Zásah do XML: bloky `<drone slot="2" …>` (kap. 5).
3. **Dělení práce: dvoustranné procházení zbývajících legů.** Seznam legů pole se spočítá jako dnes (`buildLegs`), rozdělí se v bodě `P` podle odhadu času obou dronů: dron 1 bere prefix, dron 2 bere zbytek **pozpátku** (od vzdáleného konce pole k prostředku). Rozdělení se počítá znovu při každém startu dávky ze zbývající práce (pamět pokrytí je sdílená), kolizi s rozletěnou dávkou druhého dronu brání rezervace jeho zbývajících postřikových úseků. Bez nového stavu k synchronizaci (kap. 2).
4. **Vzdušná kolize:** (a) disjunktní pásy na poli, (b) výškové vrstvy přeletu (dron 2 o `LAYER_GAP` = 6 m výš: `transitHeight`, `obstacleClearance` a `maxTransitHeight` + 6), (c) brána plošin (nevzlétnout, když druhý dron letí nad plošinou), (d) volitelná dynamická pojistka „dron v cestě“ (etapa 7, vypínatelná).
5. **Sdílené zdroje:** jedna hadice a čerpadlo = fronta FIFO (rozhoduje server, `hoseWanted` se synchronizuje); nabíječka se nezamyká (výměny jsou nezávislé, fond je jedna tabulka `spec.batteries`, atomicky v jednom snímku serveru); centrála, nafta, mixér, bedna, žebřík, hotspot beze změny.
6. **Síť/savegame:** blok dronu 1 v `writeState` se nemění; k němu se pro `numDrones > 1` jen **přilepí** blok dronu 2 a pár nových polí. Savegame: staré atributy = dron 1, nové `drone2#…` a `battery(?)#drone`; starý soubor se načte beze změny.
7. **Odhad:** 8 etap, ≈ 16 pracovních dnů programátora, ≈ 1 300 řádků Lua změněno / přidáno z 10,8 tis. (kap. 7). Etapa 1 je čistý refaktor se zárukou „1 dron beze změny chování“ ověřitelnou čtením a skriptem `tools/audit_spec_fields.py`.

Co z toho Pavel musí potvrdit, je v kap. 8.2.

---

## 1. Architektura

### 1.1 Fakta o stávajícím kódu, na kterých to stojí

- Všechno je `SprayDroneStation.fn(self, …)` s `local spec = self[SprayDroneStation.SPEC_NAME]` (Station 107×, Service 13×, Pad 11×, Planner 11×). Jedna tabulka `spec` nese všech **188 polí** (kap. 1.5), z toho 98 patří jednomu dronu (stav, uzly, cache).
- `SprayDroneRoute.lua` je čistá geometrie: veškerý stav dronu mu přichází přes `p` (`getFlightParams`, Station 1373) a `legs`. Plánování dávek (`planBatch` 1760, `splitIntoBatches` 2081) tedy **nemusí znát počet dronů**.
- `startNextBatch` (Station 2070) si trasu **vždy přepočítá z pokrytí** (`buildLegs` → `planBatchWithSwap`), takže práce je bezestavová vůči „kdo co už udělal“. To je klíčová vlastnost pro sdílení pole (kap. 2).
- Nabíječka a centrála jsou už zobecněné na N baterií (`getBestSlottedBattery` 1913, `updatePower` 2019, `getNumChargingBatteries` 1999, `updateChargerLeds`); zadrátované jsou jen `BATTERY_SLOTS = 5` (řádek 66), `BATTERY_SLOT_BITS = 3` (68) a význam `slot == 0` = „v dronu“.
- Toolbox (2142 řádků) sahá do `spec` jen na `toolbox`, `dirtyFlag`, `fillUnitIndex`, `dieselFillUnitIndex`, `concentrateFillUnitIndex` — všechno vozidlové. **Zůstává beze změny.** `SprayDroneMixer` je čistý.

### 1.2 Zvažované varianty

| | A: `spec.drones[k]` + parametr `d` do všech funkcí | B: symetrické pohledy (`spec` jen vozidlo, `drones[1..2]` oba pohledy) | **C: dron 1 = `spec`, dron 2 = pohled, `runAs`** |
|---|---|---|---|
| zásah do existujícího kódu | ~1 000 výskytů per-drone polí přejmenovat (`spec.x` → `d.x`), ~300 volání upravit | ~60 míst (vstupní body), ale všechna volání musí být v kontextu, jinak čtou prázdný `spec` | ~60 míst (vstupní body), nezapomenuté volání čte stav dronu 1 (chyba viditelná, ne pád) |
| 1 dron po etapě 1 | jiný kód všude | jiný kód (vše přes pohled) | **tentýž kód** (`runAs(1)` nepřepíná) |
| ověření čtením | mechanicky, ale obrovský diff; zapomenuté pole = nil nebo cizí dron | seznam vstupních bodů | seznam vstupních bodů + skript klasifikace polí |
| riziko | překlep v tisících míst | zapomenutý vstupní bod = nil v logu | zapomenutý vstupní bod = chová se jako dron 1; chybně klasifikované pole = „cizí“ stav |
| nová pole do budoucna | musí se rozhodnout, kam patří | stejně | stejně (+ varování za běhu, kap. 1.3) |

Doporučuji **C**. Nevýhody C a jejich opatření:

1. *Kontext je „skrytý parametr“.* Opatření: pravidlo „kontext se mění jen na 3 místech“ (kap. 1.4), skript `tools/audit_spec_fields.py` (kap. 7.3) vypíše pro každou funkci, která pole čte, a označí **smíšené** funkce, které se musí rozdělit.
2. *Chyba uvnitř `fn` nesmí nechat dosazený pohled.* `runAs` používá `xpcall` a pohled vždy vrátí, výjimku pošle dál (kód níže).
3. *Closures v `getFlightParams` (Station 1403–1414) chytají `self`, ne `spec`.* Plánovací funkce je volají synchronně uvnitř téhož `runAs`, takže vidí správný kontext. **`p` se nesmí ukládat do pole a volat později.** (Dnes se neukládá.)
4. *Neklasifikované pole za běhu.* Metatabulka pohledu při prvním zápisu neznámého klíče zaloguje `Logging.warning` — jen záchranná síť; hlavní kontrola je statická (skript).

### 1.3 Mechanismus (kód je závazný, vložit do nového `scripts/SprayDroneDrones.lua`)

```lua
SprayDroneDrones = {}

-- SHARED i DRONE se plní z tabulky v kap. 1.5; jediný zdroj pravdy je scripts/SprayDroneFields.lua
-- (SprayDroneFields.shared, SprayDroneFields.drone = pole jmen), čte ho i tools/audit_spec_fields.py.
local function toSet(list) local s = {} for _, n in ipairs(list) do s[n] = true end return s end
SprayDroneDrones.SHARED = toSet(SprayDroneFields.shared)
SprayDroneDrones.DRONE = toSet(SprayDroneFields.drone)

function SprayDroneDrones.createView(root, index)
    local SHARED, DRONE, warned = SprayDroneDrones.SHARED, SprayDroneDrones.DRONE, {}
    local view = { rootSpec = root, droneIndex = index }
    return setmetatable(view, {
        __index = function(_, k)
            if SHARED[k] then return root[k] end
            return nil
        end,
        __newindex = function(t, k, v)
            if SHARED[k] then
                root[k] = v
            else
                if not DRONE[k] and not warned[k] then
                    warned[k] = true
                    Logging.warning("SDT: spec.%s není klasifikováno (sdílené / dron)", tostring(k))
                end
                rawset(t, k, v)
            end
        end })
end

-- Dosadí na dobu fn pohled dronu k jako self[SPEC_NAME]. Dron 1 je root (nic se nepřepíná).
function SprayDroneDrones.runAs(self, k, fn, ...)
    local name = SprayDroneStation.SPEC_NAME
    local current = self[name]
    local root = rawget(current, "rootSpec") or current
    local target = root.drones[k]
    if target == nil then
        return nil                      -- dron k na vozidle není: fn se nevolá
    end
    if target == current then
        return fn(self, ...)
    end
    local args, n = { ... }, select("#", ...)
    self[name] = target
    local ok, a, b, c = xpcall(function() return fn(self, unpack(args, 1, n)) end,
        function(e) return debug.traceback(tostring(e), 2) end)
    self[name] = current
    if not ok then error(a, 0) end
    return a, b, c
end

function SprayDroneDrones.forEach(self, fn, ...)
    local root = SprayDroneDrones.getRoot(self)
    for k = 1, root.numDrones do
        SprayDroneDrones.runAs(self, k, fn, ...)
    end
end

function SprayDroneDrones.getRoot(self)
    local s = self[SprayDroneStation.SPEC_NAME]
    return rawget(s, "rootSpec") or s
end
```

Vlastnosti, které se musí dokázat čtením:

- U dronu 2 se zápis sdíleného pole **vždy** přesměruje do `spec` (klíč se v pohledu nikdy nevyskytne jako raw, takže `__newindex` platí pokaždé). Čtení per-drone pole, které dron 2 ještě nenastavil, vrací `nil`, **ne hodnotu dronu 1** (proto `__index` neodkazuje na `spec` bez výjimky).
- `runAs` je vnoření-bezpečné: `current` se obnoví, i když se volá z kontextu dronu 2 pro dron 1 (`root.drones[1] == root`).
- Pro `numDrones == 1` je `spec.drones = { spec }` a `forEach` běží jednou bez přepnutí.
- Testovatelné v LuaJIT (lupa): `tools/test_drone_view.py` — vlastnosti výše + sdílený zápis z pohledu + pád `fn` (kap. 7.3).

Inicializace: `onLoad` na konci (po načtení vlek-úrovňových dat) vytvoří `spec.numDrones`, `spec.drones = { spec }`; je-li v XML aspoň u vybrané varianty blok `slot="2"` a `spec.hasDrone`, přidá `view2 = createView(spec, 2)` a spustí `runAs(self, 2, SprayDroneStation.loadDrone, xml, key)` (kap. 1.6).

### 1.4 Pravidla pro kontext (invarianty)

1. **Kontext se mění jen v těchto místech:** `onUpdate` (smyčka přes drony, kap. 1.6), vstupní body zvenku (`sprayDroneCommand`, `setSprayDroneTransfer`, `writeState/readState`, `saveToXMLFile`, `onLoad`, `onDelete`, `getFillLevelInformation`, `getIsFoldAllowed`), plánovač a debug. Uvnitř jiné funkce se `runAs` nevolá, kromě `forEach`/„pro druhého dronu“ v arbitru a v rezervacích (kap. 2.4, 3.1).
2. **Funkce, která sahá na per-drone pole, se volá jen v kontextu dronu.** Funkce, která sahá jen na sdílená pole, smí běžet v libovolném. **Smíšená** funkce (obojí) je v pořádku, pokud dostává dron kontextem a sdílené pole čte přes pohled (to dělá). Problém je jen funkce, která v **vozidlovém kontextu** (root = dron 1) sahá na per-drone pole a míní „všechny drony“ — takové jsou v kap. 1.6 označeny V→D (≈ 20) a každá se přepíše na smyčku přes `forEach`.
3. **Dron 1 v vozidlovém kontextu = root.** Proto každá vozidlová funkce, která dnes čte `spec.state`, `spec.droneFillLevel` atd., čte po refaktoru stav **dronu 1** — a v kap. 1.6 je označeno, kde se musí místo toho smyčkou projít oba.
4. **Priorita při souběhu:** v jednom snímku serveru se drony zpracují v pořadí 1, 2. Rozhodnutí arbitra (hadice) se dělá před smyčkou, takže drony vidí konzistentní stav.
5. **Žádné nové per-drone pole bez zápisu do `SprayDroneFields`.** Skript to hlídá (selže, pokud `spec.<jméno>` není v žádném seznamu nebo je v obou).

### 1.5 Klasifikace všech 188 polí `spec`

Zdroj: `grep -oE "spec\.[A-Za-z_][A-Za-z0-9_]*"` přes `scripts/**/*.lua` (188 jmen; včetně polí zapisovaných dynamicky přes `spec[setting.key]`). V = vozidlo (sdílené), D = dron k (per-drone).

**V1: konstanty z XML (načtou se jednou, oba drony je mají stejné, protože mají tutéž variantu)** — 48 polí:
`acceleration`, `ascentSpeed`, `batteryCapacity`, `batteryKey`, `batteryKwh`, `batteryMass`, `batteryReserve`, `batterySwapBelow`, `batteryVariant`, `chargeRate`, `climbFactor`, `climbSpeed`, `concentrateFillUnitIndex`, `corridorHeight`, `cruiseSpeed`, `descentFactor`, `dieselFillUnitIndex`, `dieselPerSecond`, `drainRate`, `droneMass`, `droneName`, `droneRadius`, `fillUnitIndex`, `hoverFactor`, `maxRange`, `maxTransitHeight`, `mixerRatios`, `mixerTypes`, `navBlinkOn`, `navBlinkPeriod`, `navLightIntensity`, `palletDistance`, `palletRate`, `pumpRate`, `rangeCap`, `readyCharge`, `rotorPitch`, `securedFoldTime`, `sprayHeight`, `sprayingSpeed`, `swapTime`, `tankCapacity`, `trailerFoldEnd`, `turnAcceleration`, `usageScale`, `variants`, `workWidth`, `yawSpeed`.

**V2: sdílený běhový stav a nastavení** — 42 polí:

| pole | poznámka |
|---|---|
| `fieldId`, `flightAreas`, `areaVersion` | jedno pole, jedna letová plocha; `areaVersion` zneplatňuje koridory obou dronů |
| `transitHeight`, `obstacleClearance`, `sideClearance`, `headlands`, `headlandFirst`, `settingsVersion` | nastavení letu z plánovače (jedno pro oba); vrstvy dronu 2 se přičítají v `getFlightParams` (kap. 2.5), ne v poli |
| `coverage`, `coverageDirtyFlag`, `coverageSyncTime` | **sdílená pamět pokrytí** |
| `dirtyFlag` | jeden dirty flag; blok dronu 2 se píše do téhož streamu (kap. 4.1) |
| `batteries`, `batteryNodes`, `batteryParents`, `batteryShown`, `batteryMoves`, `batterySlotDeck`, `batteryStowed`, `chargerLeds`, `chargerLedShown`, `lastFoldProgress`, `numCharging` | fond baterií a jeho modely (kap. 3.3); každá baterie dostane `battery.drone` |
| `generatorEnabled`, `generatorRunning`, `exhaust`, `powerSyncTimer`, `powerDebugTimer`, `sound` | centrála, výfuk a zvuky vleku |
| `hose`, `hoseT` | jedna hadice; nové `hoseWanted` (kap. 3.1) |
| `transferMode`, `transferPallet`, `transferPalletUnit`, `palletSearchTime`, `transferSyncTimer` | přečerpávání; nové `transferDrone` |
| `toolbox`, `ladder`, `actionEvents`, `frozen`, `debugCommandId` | bedna, žebřík, vstupy, zmrazení fyziky vleku, ladění |

**D: per-drone** — 98 polí:

| skupina | pole |
|---|---|
| let a poloha | `airborne`, `avoidClimbTo`, `avoidHeight`, `avoidRayLength`, `batch`, `batchHeight`, `flightTime`, `isLinked`, `isSpraying`, `lastSprayTime`, `lastWorldPos`, `moveDir`, `netTarget`, `path`, `pos`, `speed`, `sprayFrom`, `sprayTypeIndex`, `litersPerMeter`, `massPerLiter`, `velocity`, `worldAccel`, `wpIndex`, `yawRate`, `drainPos`, `drainFactor`, `tilt` |
| stav mise | `state`, `status`, `missionActive`, `serviceTimer`, `swapChecked`, `swapPending`, `swapTimer`, `isPumping`, `isMixing`, `isSwapping`, `waitingForCharge`, `batteryAtStart`, `estimatedEnergy`, `estimatedTime` |
| náplň a baterie dronu | `battery`, `droneBattery`, `droneFillLevel`, `droneFillType` |
| trasa a cache | `corridor`, `drawLegs`, `hopCache`, `numBatches`, `pathCache`, `pathCacheSize`, `range`, `rangeKey`, `routeClipped`, `routeDirty`, `routeInfo`, `routeTimer`, `transitCache`, `transitCacheSize` |
| uzly a vizuál | `appliedUnfold`, `unfold`, `unfoldMoving`, `batterySlotDrone`, `clamps`, `clampsVisible`, `droneKey`, `dronePrefix`, `effects`, `foldParts`, `hasDrone`, `hotspot`, `hotspotFailed`, `localRot`, `localTrans`, `navLights`, `node`, `parent`, `pad`, `propBlades`, `propPaintMaterial`, `propSource`, `rotors`, `rotorSpeed`, `rotorsParked`, `rotorVolumeScale`, `samples`, `soundPitch`, `soundVolume`, `soundDebugPlaying`, `soundDebugTimer`, `sprayEffectPlacement`, `sprayEffectsActive`, `sprayEffectsPlaced`, `sprayEffectsShown`, `tiltNode` |
| ladění | `debugLoopDetached`, `debugT`, `debugTimer` |

(Součet V1 48 + V2 42 + D 98 = 188, ověřeno skriptem proti `grep` zdrojů. Po přidání polí z kap. 1.7 se seznamy v `SprayDroneFields.lua` rozšíří.)

Zdůvodnění nejsporných:

- `unfold`, `appliedUnfold`, `unfoldMoving`: čas skládání vleku je společný, ale rozložení je „zamrzlé“ pro dron ve vzduchu (`updateDroneParts`, Station 2649–2660 jen pro `isLinked`), takže je per-drone.
- `isPumping/isMixing/isSwapping/waitingForCharge/swapTimer/swapChecked/swapPending`: stav servisu daného dronu. Zvuk mixéru čte `isMixing` obou (kap. 3.4), `setState` (1728) nuluje jen vlastní.
- `hopCache`: klíč nezahrnuje vrstvu přeletu (dron 2 má vyšší `obstacleClearance`), proto per-drone. (Existující nedostatek: cache se při změně nastavení nemaže; mimo rozsah.)
- `corridor`, `pathCache`, `transitCache`: závisí na poloze domova (`setCorridorHome`, Station 1151), tedy per-drone. Graf plochy se postaví dvakrát (O(n²) viditelnost při změně plochy; zanedbatelné).
- `range`, `rangeKey`: závisí na výšce plošiny a na vrstvě; kruh dosahu se kreslí jednou (z dronu 1).
- `pad`: `SprayDronePad` zůstává jen pro dron 1 (Mini). Max nemá `padTray` → `spec.pad == nil`.
- `propPaintMaterial`: zdrojový materiál z prvního listu vlastního dronu.
- `samples`, `soundPitch`, `soundVolume`, `rotorVolumeScale`: každý dron má vlastní vzorek rotorů (vlastní `linkNode`).
- `missionActive`: per-drone, aby šlo dron 2 vrátit samostatně a aby jeden dron s vybitou baterií neukončil misi druhému.

### 1.6 Klíčové funkce: kontext a změna

Legenda: **V** = vozidlový kontext, **D** = v kontextu dronu, **V→D** = vozidlová funkce, která uvnitř volá D funkce smyčkou, **S** = rozdělit na V a D část.

**Station.lua**

| funkce (řádek) | ctx | změna |
|---|---|---|
| `initSpecialization` (249) | V | + `drone(?)#slot`, `power#slots`, savegame cesty z kap. 4.3 |
| `registerDronePartPaths` (208) | — | beze změny (platí pro `drone(?)` včetně slot 2) |
| `loadDroneVariant` (386) | S | slot 1 jako dnes; pro slot 2 sbírá `spec.variants[i].key2/prefix2`; vrací `hasDrone` pro dron 2 jako `numDrones >= 2` |
| `onLoad` (568) | S | rozdělit na `loadVehicle` (586–663: konstanty, mixér, baterie, `loadServiceParts`) a `loadDrone(self, xml, key)` (665–750: uzly, stav, zvuky, efekty, koridor) volanou `runAs` pro každý dron; **před smyčkou `SETTINGS` (623) inicializovat `spec.activeDrones = spec.numDrones`**, jinak `nil + 0.5` |
| `saveToXMLFile` (831), `onDelete` (871) | V→D | smyčka přes drony (uložení `drone2`, `attachDrone`, `deleteSamples`, `deleteEffects`, `Hotspot.delete`) |
| `getIsFoldAllowed` (894) | V→D | „všichni zaparkovaní“ a „žádný nemá `rotorSpeed > 0` / `not rotorsParked`“; `RETURN_HOME` pro všechny |
| `getFillLevelInformation` (919) | V→D | řádky dronů sloučit do **jednoho** (součet litrů a kapacit), jinak je jich 6 a vanilla kreslí nejvýš 5 (kap. 8.1 bod 9) |
| `getSprayDroneIsParked` (985) | V→D | `true` jen když jsou všechny drony `PARKED/SERVICING` |
| `getHomePosition` (993), `getHomeYaw` (1006) | D | beze změny (čtou `spec.node/parent/localTrans`) |
| `setSprayDroneSettings` (1014), `changeSetting` (1046) | V | po změně `routeDirty = true` a smazat `transitCache` **u všech dronů** (`forEach`) |
| `updateRange` (1064), `getIsTurnClear` (1090), `getCorridor` (1137), `getHomePath` (1159), `getTransit` (1185), `getUseExtension` (1204), `makeTransit` (1218), `getHopHeight` (1420) | D | `makeTransit`: `minHeight` (`transitHeight` / `corridorHeight`) + vrstva dronu (kap. 2.5); ostatní beze změny |
| `getFlightArea` (1114), `setSprayDroneFlightArea` (1120) | V | po změně plochy `routeDirty` všem dronům |
| `getFlightParams` (1373) | D | + vrstva: `transitHeight`, `obstacleClearance`, `maxTransitHeight` o `spec.layerOffset` |
| `getFillSource` (1317), `getConcentrateUnit` (1306), `takeFromTrailer` (1779), `loadMixer` (1286) | V | beze změny |
| `getSprayType` (1346), `getMassPerLiter` (1364) | D | beze změny (čtou náplň dronu) |
| `getFieldAllowed` (1469) | V | volat v kontextu dronu 1 (rozsah z jeho domova) |
| `getRouteSummary` (1507) | D + V | po dronu; navíc `getRouteSummaryAll` pro plánovač (kap. 6) |
| `getPowerParams` (1582) | D | `spares`: fond rozdělit podle pořadí nabití mezi aktivní drony (kap. 2.7); `droneHasBattery` z dronu |
| `buildLegs` (1606) | V | splitnout: `buildAllLegs(self)` (jako dnes, domov dronu 1, rezervace druhého dronu) + `SprayDroneRoute.splitLegs` pro dron k (kap. 2.2) |
| `raiseCoverage` (1620), `clearCoverage` (1628) | V | `clearCoverage` nastaví `routeDirty` všem dronům |
| `updateRoutePreview` (1635) | V→D | orchestrace: jednou `buildAllLegs`, pak per-drone `splitIntoBatches`; zpoždění druhého dronu o 2,5 s (výkon, kap. 8.1) |
| `sprayDroneCommand` (1668) | V→D | signatura `(command, fieldId, noEventSend, droneIndex)` (4. parametr přidán na konec, aby stará volání platila); `START/RETURN_HOME` s `droneIndex == 0` = všechny aktivní drony, jinak jeden; `SELECT_FIELD`, `RESET_FIELD`, `SET_GENERATOR` vozidlové |
| `setState` (1728) | D | beze změny |
| `detachDrone/attachDrone/setDroneWorldPosition` (1745–1775) | D | beze změny |
| `pumpDrone` (1794) | D | brána hadice (kap. 3.1): vrací `(filling, mixing, waiting)`; `waiting` se v `updateService` počítá jako „zaneprázdněn“ |
| `updateService` (1819) | D | viz kap. 3.1; podmínka konce `serviceTimer > 0 or pumping or waiting or swapping` |
| `getWantsSwap` (1862), `swapBattery` (1965), `loadDroneBattery` (1949), `unloadDroneBattery` (1932), `syncDroneBatteryCharge` (1924), `updateBatteryPlacement` (1983) | D | `battery.drone = k` při `slot = 0` (kap. 3.3); `loadDroneBattery`/`swap` sdílejí fond |
| `getBatteryInSlot`, `getFreeBatterySlot`, `getBestSlottedBattery`, `getNumChargingBatteries`, `getCanCharge`, `updatePower` (1893–2059) | V | `BATTERY_SLOTS` → `spec.numBatterySlots` |
| `endMission` (2061) | D | `STATUS_FIELD_DONE` + `clearCoverage` jen když druhý dron neletí a nezbývá nic (kap. 2.6) |
| `startNextBatch` (2070) | D | `#legs == 0` ≠ „pole hotové“ (kap. 2.6); legy z `splitLegs` (kap. 2.2); rezervace přes `spec.path` (kap. 2.4) |
| `startReturnHome` (2152), `flushSpray` (2189), `getReturnEnergy` (2234), `drainBattery` (2264), `getLookaheadSpeed` (2291), `getIsPathBlocked` (2334), `updateYaw` (2372), `updateFlight` (2383) | D | `updateFlight` 2395: `spec.hoseT > 0` → `hose.drone == k and hoseT > 0`; brána plošiny (kap. 2.5); pojistka „dron v cestě“ v `getIsPathBlocked` až v etapě 7 |
| `updateDroneParts` (2611) | S | D část (rotory, unfold, tilt, zvuk rotorů, efekt, LED, hotspot) × dron; V část (`updateGenerator`, `SprayDroneSound.updateSounds`, `updateServiceVisuals`) **jednou** |
| `applyFold`, `applyNavLights`, `updateRotorSound`, `updateSprayEffects`, `updateTilt`, `getNozzlePositions`, `placeSprayEffects` (2564–2923) | D | beze změny |
| `updateFreeze` (2927) | V | beze změny |
| `onUpdate` (2939) | V→D | viz kap. 1.8 |
| `refreshRoutePreview` (3010), `updatePilotView` (3021), `drawHudTexts` (3080) | V→D | kruh dosahu jednou, čáry tras a HUD řádek per dron |
| `getDroneStateName` (3128), `getDroneStateText` (3155) | D | `getDroneStateName`: nový stav „čeká na hadici“ |
| `getMixerText` (3114) | V | čte `isMixing` libovolného dronu |
| `getCanStart` (3248), `getCanReturnHome` (3253), `getCanSelectField` (3243), `startFlight` (3272), `selectField` (3259) | V→D | „aspoň jeden“ / „všichni“, viz kap. 6 |
| `writeState/readState` (3325/3357), `onWrite/ReadStream`, `onWrite/ReadUpdateStream` (3421–3472) | V→D | kap. 4.1 |
| `updateClientInterpolation` (3406) | D | smyčka přes drony v `onUpdate` |

**Service.lua**

| funkce (řádek) | ctx | změna |
|---|---|---|
| `loadServiceParts` (40) | S | `clamps`, `batterySlotDrone`, `hose.port/via` per dron (volat v kontextu dronu), baterie a hadice jednou; `hose.ports[k]`, `hose.vias[k]` (kap. 3.1); smyčky `BATTERY_SLOTS` → `numBatterySlots` |
| `updateChargerLeds` (132) | V | beze změny (délka z `numBatterySlots`) |
| `updateServiceVisuals` (165) | S | `clamps` (167–173) per dron; baterie (197–234) **pro oba**: `freeSlot` počítat sekvenčně pro každou baterii se `slot == 0` a `batteryStowed`, jinak by se dvě skládané baterie posadily do téhož slotu; cíl `batterySlotDrone[battery.drone]`; hadice (238–299) podle `hose.drone` (kap. 3.1) |
| `startBatteryMove` (319) | V | `toDrone` = rodič je `batterySlotDrone` **kteréhokoli** dronu |
| `layoutHose`, helpers (376–655) | V | beze změny (pracují s `hose.port/via`; arbitr je nastaví na aktuální) |
| `setSprayDroneTransfer` (659), `getCanTransfer` (687), `updateTransfer` (738), `getCanAcceptDrained` (681), `actionEventDrainDrone` (778) | V→D | `transferDrone`; `getCanTransfer(DRAIN)` a `drain` větev `updateTransfer` běží v kontextu `transferDrone` |
| `getTransferPallet`, `actionEventPumpToPallet`, `getTransferText` | V | beze změny |

**Ostatní:** `SprayDronePad` (jen dron 1), `SprayDroneHotspot.update(spec, flying)` (D; volá se v kontextu dronu), `SprayDroneLadder`, `SprayDroneToolbox`, `SprayDroneMixer` beze změny. `SprayDroneSound.updateSounds` (85): `target = spec[def.driver] == true` → pro `isMixing` `anyDrone(self, "isMixing")` (3 řádky). `SprayDroneDebug.runCommand`: `chargeAll` (209–216) smyčkou přes drony; `coverField` (294) vozidlové; `update` (85) se volá jednou v `onUpdate` před smyčkou dronů.

### 1.7 Nová pole

- V: `numDrones` (1 / 2 z XML), `drones` (pole pohledů, `drones[1] == spec`), `activeDrones` (nastavení 1..`numDrones`), `numBatterySlots`, `batterySlotBits`, `hoseWanted` (0 = nikdo, 1/2; synchronizované), `transferDrone`, `layerGap`.
- D: `droneIndex` (v pohledu; pro dron 1 `spec.droneIndex = 1`), `layerOffset` (`(index − 1) · layerGap`), `serviceArrival` (čas příchodu do SERVICING, pro FIFO), `waitingForHose`.
- Baterie: `battery.drone` (1/2, platí jen pro `slot == 0`).
- Hadice: `hose.ports[k]`, `hose.vias[k]`, `hose.drone` (právě zobrazený cíl).

### 1.8 `onUpdate` po refaktoru (pseudokód; pořadí je závazné)

```lua
function SprayDroneStation:onUpdate(dt, ...)
    local spec = SprayDroneDrones.getRoot(self)
    SprayDronePad.update(self, dt)                                    -- jen dron 1 / Mini
    SprayDroneDrones.forEach(self, SprayDroneStation.updateDroneVisual, dt)   -- rotory, unfold, tilt, LED, efekt, zvuk rotorů, hotspot
    SprayDroneStation.updateVehicleVisual(self, dt)                   -- generátor, zvuky vleku, baterie/nabíječka, hadice, úchyty
    if self.isServer then
        local simDt = dt * SprayDroneDebug.update(self, dt)
        SprayDroneStation.updateServiceArbiter(self, simDt)           -- hadice (nový), jen numDrones > 1
        SprayDroneDrones.forEach(self, SprayDroneStation.updateDroneLogic, simDt)  -- FLYING/RETURNING -> updateFlight, SERVICING -> updateService
        SprayDroneStation.updateFreeze(self)
        SprayDroneDrones.forEach(self, SprayDroneStation.updateBatteryPlacement)
        SprayDroneStation.updatePower(self, dt)
        SprayDroneStation.updateTransfer(self, dt)
    else
        SprayDroneDrones.forEach(self, SprayDroneStation.updateClientInterpolation, dt)  -- jen hasDrone
    end
    -- raiseActive: OR přes drony (state ~= PARKED, rotorSpeed > 0, not rotorsParked, unfoldMoving)
    --              + generatorRunning, hoseT > 0, transferMode, SprayDronePad.needsUpdate, getCanCharge
    -- pilot: updatePilotView / drawPreview: vozidlové, čáry tras per dron
end
```

`updateDroneVisual` = stávající `updateDroneParts` bez `updateGenerator`, `SprayDroneSound.updateSounds`, `updateServiceVisuals` a bez `debugMistLoop` (ten jen pro dron 1). `updateVehicleVisual` = tyto tři volání + zpracování clamp/baterií/hadice.

---

## 2. Dělení práce na jednom poli

### 2.1 Z čeho vycházíme (stávající chování)

- `SprayDroneRoute.buildLegs` (Route 840–949) vyrobí **seřazený** seznam legů `{x1,z1,x2,z2,len}`: řádky rovnoběžné s nejdelší hranou, pruhy číslované `k` od `minN`, řazené od strany bližší domovu (857–863), boustrophedon (`forward` se přepíná, 866–911); s `headlands > 0` jsou na začátku nebo na konci smyčky úvratí a kolem ostrovů (916–948).
- Pokrytí (`markCovered`, 427) se zapisuje po pruzích `k` / po obloucích smyček; `getCoverage` ho vrací per pole+druh postřiku+záběr+počet úvratí; `encode/decodeCoverage` (529/543) ho přenáší po síti. Zápis je **symetrický vůči směru letu** (`t1 > t2` se prohodí, 466; `storeLoopInterval` 401 prohazuje `s1 > s2`), takže leg letěný pozpátku se zapíše stejně.
- `planBatch` (1760) bere legy po řadě od `(legIndex, offset)`, kolik zvládne nádrž a baterie; po dávce `startNextBatch` začíná od nuly s novým pokrytím.

### 2.2 Algoritmus: dvoustranné rozdělení zbývajících legů

Nová čistá funkce v `SprayDroneRoute.lua` (testovatelná v lupa):

```lua
-- legs: seřazený seznam z buildLegs (zbývající práce); n = počet aktivních dronů (1 nebo 2)
-- opts: { homes = {{x,z},{x,z}}, tankLength, cruise, spraying, service, minSplit, requester }
-- vrací { legs1, legs2 }; legs2 je zbytek seznamu v OBRÁCENÉM pořadí a s obrácenými úseky
function SprayDroneRoute.splitLegs(legs, n, opts)
```

1. `W = Σ len`. Je-li `n == 1` nebo `W < opts.minSplit` (výchozí 60 m, tj. práce na jednu krátkou dávku), vrátí všechno `requester` (dron, který o práci žádá; v náhledu dron 1) a druhému `{}`.
2. Prefixové sumy `C[i] = Σ_{j≤i} len_j`, `Cd1[i] = Σ len_j · dist(home1, střed leg j)` a sufixové `Cd2[i]` s `home2`.
3. Pro každé `i = 0..N` (řez za legem `i`) odhad času
   `T1(i) = C[i] / vSpray + ceil(C[i] / Lb) · (2 · d1(i) / vCruise + tService)`, `d1(i) = Cd1[i] / C[i]`,
   `T2(i) = (W − C[i]) / vSpray + ceil((W − C[i]) / Lb) · (2 · d2(i) / vCruise + tService)`, `d2` obdobně ze sufixu.
   `Lb = min(tankLiters / litersPerMeter, 0,7 · batteryCapacity · vSpray)` je délka postřiku jedné dávky (nádrž a baterie). Zvolí se `i` minimalizující `max(T1, T2)` (při shodě menší `i`). O(N).
4. `legs1 = legs[1..i]`; `legs2 = reverse(legs[i+1..N])`, kde `reverse` obrátí pořadí **i každý leg** (`x1,z1 ↔ x2,z2`). Boustrophedon zůstane souvislý (konec legu `j` leží u začátku `j+1`, po obrácení naopak).

Vlastnosti:

- Dron 1 pracuje od strany blíž vleku (jako dnes), dron 2 od opačného konce pole k prostředku. Pásy jsou disjunktní a **sousední řádky mají rozteč `workWidth`** (S 6 m, M 9 m, L 11 m) proti `2 · droneRadius + 0,6` (3,3 / 3,8 / 3,9 m): drony se na poli nepotkají. Otočky mezi řádky jsou půlkruhy uvnitř vlastního pásu (`rowTurn`, Route 1714).
- S úvratěmi (`headlandFirst = 1`) je seznam `[úvrať 1 + ostrovy, úvrať 2 …, řádky…]`; řez `i` pak dá dronu 1 vnější smyčky a první řádky, dronu 2 řádky od konce pole pozpátku. Vyvažování podle délky řez posune. Úvrati s jedinou smyčkou se řez dá rozdělit vodorovně: dron 1 jede smyčku dopředu od vrcholu nejblíž domovu, dron 2 pozpátku (zbytek smyčky) — rozbíhají se a potkají na opačné straně.
- **Pokrytí zůstává sdílené** (`spec.coverage`): oba drony do něj píší přes `markCovered` v `flushSpray` (2189). Dva současné zápisy v jednom snímku jsou bezpečné (jednovláknové, v tabulce). `coverageDirtyFlag` se zvedá z obou. `getCoverage` vyžaduje stejný druh postřiku, záběr a počet úvratí: oba drony mají tutéž variantu (stejný záběr) a plní se z téže nádrže (`pumpDrone` zahodí zbytek jiného druhu), takže záznam nekmitá (kap. 8.1 bod 11).

### 2.3 Rozdělení se přepočítává při každé dávce

`startNextBatch(drone k)` volá `buildAllLegs` (zbývající legy z aktuálního pokrytí, **bez** rezervovaných úseků druhého dronu, kap. 2.4) a `splitLegs`; dron `k` plánuje svůj seznam. Žádný trvalý stav „zóna“ ani vlastník pruhu se neukládá ani neposílá:

- *Úplnost:* co žádný z dronů nevzal, zůstane v pokrytí neoznačeno a při příští dávce kteréhokoli dronu se znovu nabídne.
- *Bez překryvu:* druhý dron rezervuje své zbývající postřikové úseky (kap. 2.4), takže si je první nevezme.
- *Vyvažování samo:* když dron 1 postupuje rychleji, zbývající práce je menší na jeho straně a řez `i` se při příští dávce posune k dronu 2. Konvergují k prostředku.
- *Konec:* když zbývá méně než `minSplit`, bere všechno žadatel; druhý dron nedostane práci a skončí bez hlášení „pole hotové“ (kap. 2.6).
- *Klient:* plánovač počítá náhled týmž `splitLegs` z týchž synchronizovaných dat (pokrytí, plocha, nastavení), jen bez rezervací (ty znají jen server). Náhled je odhad, jako dnes.

### 2.4 Rezervace (jen server)

Rezervace se **neukládá**, odvozuje se z `path` druhého dronu: pro každý waypoint `wp.spray` od `wpIndex` dál úsek `(wp.sx, wp.sz) → (wp.x, wp.z)` + aktuální `sprayFrom → pos`. Nová funkce `SprayDroneStation.getReservedSegments(self, k)` (kontext vozidlový, pro dron `j ≠ k` ve stavu `FLYING` s `path ~= nil`; stav `path` se nastaví hned v `startNextBatch`, takže rezervace platí od startu dávky). `buildAllLegs` předá segmenty do `SprayDroneRoute.buildLegs(…, reserved)`, který je v `appendNeededParts` (Route 988) a v `needsAt` smyček úvratí (`buildHeadlandLegs` 697, `buildIslandLegs` 780) vyloučí: bod `(px, pz)` je rezervovaný, je-li blíž než `workWidth / 2 + 1` k některému segmentu (O(body × segmentů), segmentů ≤ ~30).

### 2.5 Kolize ve vzduchu

Pořadí od nejlevnější ochrany po nejdražší; v1 = 1–3, 4 je etapa 7 (vypínatelná `SprayDroneStation.SEPARATION_GUARD`).

1. **Disjunktní pásy na poli** (kap. 2.2), rozteč ≥ `workWidth`.
2. **Výškové vrstvy přeletu.** `layerOffset(k) = (k − 1) · LAYER_GAP`, `LAYER_GAP = 6` m (rotor 0,65 m + vír pod vrtulemi; hodnota v XML `sprayDrone#layerGap`). V `getFlightParams` přičíst k `transitHeight`, `obstacleClearance`, `maxTransitHeight` (aby `tooHigh`, Route 1606, nevyšlo dřív), v `makeTransit` k `minHeight` (`transitHeight` i `corridorHeight`, Station 1230/1244). Profil výšky (`buildTransit`, Route 1469) je invariantní vůči posunu, takže dron 2 letí všude ≥ 6 m nad dronem 1 i tam, kde výšku diktuje překážka. Nastavení „výška přeletu“ v plánovači zůstává jedno (základ). `getBatteryRange` (Route 1946) počítá s vrstvou dronu (`p.transitHeight`), takže dosah dronu 2 je o málo menší.
3. **Plošiny.** Rozteč 4,25 m > `2 · droneRadius + 0,6` (L: 3,9 m). Při načtení `loadDrone` pro dron 2: `Logging.xmlWarning`, pokud `dist(home1, home2) < 2 · droneRadius + 0,8`. Vzlet dronu `k` (v `updateFlight`, větev `not spec.airborne`, Station 2393–2402) čeká, dokud jiný dron neletí do vzdálenosti `PAD_CLEAR = 8` m vodorovně od jeho plošiny níž než `restHeight + 8` m (čtení `pos` druhého dronu přes `runAs`). Přistání takovou bránu nemá (viz 4).
4. **Dynamická pojistka** (etapa 7): v `getIsPathBlocked` (Station 2334) po rázové dráze (`length`) po waypointech zkontrolovat druhý dron: bere se jen **letící** druhý dron (`not isLinked`; stojící na plošině nepočítat — rozteč plošin je menší než bezpečnostní okruh). Konflikt = vodorovně `< SEP_H = 2 · droneRadius + 0,6` a svisle `< SEP_V = 2,5` m (absolutní výšky: terén + `pos.h`). Při konfliktu **zabrzdí oba** (`speed -= 2·acc·s`, jako dnes), ale **dron 2 navíc stoupá** přes stávající `avoidClimbTo` (Station 2459–2480), dokud konflikt trvá + `GUARD_EXTRA_CLIMB`; dron 1 po zbrzdění čeká na uvolnění. Nezablokuje se: dron 2 má neomezené stoupání (`maxTransitHeight` platí jen pro plánování), dron 1 nikdy nestoupá kvůli dronu 2. `avoidHeight` (Station 2481) nesmí klesat, dokud je dron 1 pod dronem 2 (`castRay` druhý dron nevidí, nemá kolizi; přidat podmínku). Časový limit konfliktu 20 s → `RETURN_HOME` dronu 2.

### 2.6 Konec pole, „pole hotové“, chyby

- `startNextBatch` (Station 2070) dnes při `#legs == 0` volá `clearCoverage` a `endMission(FIELD_DONE)` (2081–2085). **To musí být rozšířeno:** prázdný *vlastní* seznam není hotové pole. Nová logika: `all = buildAllLegs(self)` (bez rezervací, **bez řezu**); je-li `#all == 0` a **druhý dron už nelétá** (nemá `FLYING/RETURNING` ani `missionActive` s rozpracovanou dávkou), pak jako dnes (`clearCoverage`, `FIELD_DONE`). Je-li `#all == 0`, ale druhý dron ještě letí, dron končí tiše (`missionActive = false`, `status = STATUS_NONE`, `PARKED`); pole „dokončí“ ten, kdo přistane poslední. Je-li `#all > 0`, ale vlastní seznam by po řezu vyšel prázdný (`splitLegs` dal všechno druhému dronu), žadatel vezme celý `all` (řez se ignoruje), aby práce nezůstala bez vlastníka.
- Dron bez baterie / bez nafty / jiná chyba (`STATUS_NO_FUEL`, `STATUS_NO_AREA_PATH`, `STATUS_OBSTACLE` …) ukončí **jen svou** misi (per-drone `status`); druhý dron pokračuje (jeho další rozdělení už počítá s `n = 1`, protože `activeDrones` v kontextu = počet dronů s `missionActive`). `n` v `splitLegs` = počet dronů, které mají `missionActive` nebo právě letí; v náhledu `spec.activeDrones`.
- Stav `STATUS_*` je per-drone; plánovač zobrazí oba.

### 2.7 Náhled v plánovači: společný fond a nafta

`updateRoutePreview` plánuje oba drony **nezávisle** (`splitIntoBatches` pro dron 1 s jeho legy a pro dron 2 s jeho), přičemž:

- `p.power.spares` (Route 2077): fond baterií v nabíječce se seřadí podle nabití sestupně a rozdělí střídavě (1., 3., 5. dronu 1; 2., 4., 6. dronu 2);
- `p.power.diesel`: polovina na dron (součet spotřeby je v `info.dieselUsed`, varování `fuelRunsOut/noFuel` se sečte);
- hadice a čerpadlo jsou jeden zdroj: odhad celkového času = `max(T1, T2, Σ časů plnění obou dronů + první přelet)` (čerpadlo je sériový zdroj). Přesná simulace souběhu se nedělá.

---

## 3. Sdílené zdroje a pořadí obsluhy

### 3.1 Hadice a čerpadlo (fronta)

Jedna hadice = jedno čerpadlo = jeden dron naráz. Rozhoduje server v `updateServiceArbiter(self, dt)` (nový, jen `numDrones > 1`), před smyčkou dronů. Stavy: `IDLE` (`hoseT = 0`, `hoseWanted = 0`) → `EXTENDING` → `ATTACHED` (`hoseT = 1`) → `RETRACTING` → `IDLE`.

Vstup pro dron `k` (`wantsHose[k]`):
`(state == SERVICING and needsFill)` nebo `(transferMode == DRAIN and transferDrone == k)`,
`needsFill = droneFillLevel < tankCapacity − 0,001` a `getFillSource(self).kind ~= KIND_NONE` a `liters > 0`.

Pravidla:

| | |
|---|---|
| R1 | `hoseWanted ~= 0` a `wantsHose[hoseWanted]` trvá → zůstává. |
| R2 | `hoseWanted ~= 0` a dron už nechce (plný, nic v nádrži, stav se změnil) → `hoseWanted = 0` (hadice se zasune). |
| R3 | `hoseWanted == 0` a **server `hoseT <= 0`** a někdo chce → přidělit tomu s nejstarším `serviceArrival` (shoda → nižší index). `DRAIN` (ruční příkaz) má před plněním přednost, ale nepřerušuje běžící plnění. |
| R4 | Bez předbíhání. Doba držení je omezená objemem (≤ `tankCapacity / pumpRate`, 40–75 s). |
| R5 | Přepnutí na druhý dron = zasunutí (`HOSE_TIME` 2 s) + vysunutí (2 s). |

Brána čerpadla (`pumpDrone`, Station 1794): pro `numDrones == 1` beze změny. Pro více dronů čerpá jen když `hoseWanted == k and hose.drone == k and spec.hoseT >= 0,99`; jinak vrací `filling = false, mixing = false, waiting = needsFill`. `updateService` (1819) pak musí `waiting` počítat jako „zaneprázdněn“: bez toho podmínka konce (1843: `serviceTimer > 0 or pumping or swapping`) propustí čekající dron do `startNextBatch`, ten uvidí `droneFillLevel < 0,5` (2087) a **ukončí misi s `STATUS_TRAILER_EMPTY`** — nejzrádnější chyba celého návrhu. `isPumping` (zvuk, HUD) zůstává `filling`; `waitingForHose` pro stavový text.

Vizuál (`updateServiceVisuals`, Service 238–299), běží na serveru i klientech:

- `spec.hoseWanted` je **synchronizované** (2 bity, kap. 4.1). Zobrazený cíl `hose.drone` se mění **jen při `hoseT <= 0`** (místní stav klienta): `connect` je `true`, jen když `hoseWanted ~= 0 and (hose.drone == hoseWanted or hoseT <= 0)`; při `hoseT <= 0 and hose.drone ~= hoseWanted` se `hose.drone = hoseWanted`, `hose.port = hose.ports[hose.drone]`, `hose.via = hose.vias[hose.drone]`, `hose.appliedKey = nil`. Zbytek (`layoutHose`, Bézier k hrdlu) beze změny.
- Pro `numDrones == 1`: `connect` se počítá starým výrazem (243–245), tj. totéž chování.
- Zdroj `hoseT`: `updateService`/`updateFlight` dnes používají `spec.hoseT > 0` jako bránu vzletu (Station 2395). Po změně `hose.drone == k and spec.hoseT > 0`: hadice připojená k dronu 1 nebrání vzletu dronu 2.
- `fillHoseStart` je jeden; `hoseVia` je per dron v bloku `<drone slot=…>` a vytváří se **per dron** (`createTransformGroup("sdtHoseVia")` pod `<prefix>Tilt`, Service 90–100), znaménko `x` podle strany `fillHoseStart` vůči `Tilt` daného dronu (nezávisle).
- Dosah: při načtení `SprayDroneStation.checkHoseReach(self, k)` (adaptace `SprayDronePad.hoseReaches`, Pad 315–353, bez posunu desky): `volná délka ≥ vzdálenost pevného konce (fillHoseLay3) → hrdlo dronu k · 1,12 + 0,2`; jinak `Logging.xmlWarning` (hadice se pak natáhne, ale prověšení nesedí).

### 3.2 Nádrž, mixér, čerpadlo

Obě nádrže vleku jsou jedna `fillUnit` (index 1), tedy `getFillSource`, `takeFromTrailer`, mixér a koncentrát zůstávají. Čerpadlo plní vždy jen dron s hadicí (3.1), takže `pumpRate` 1 l/s znamená 40 s na 40 l; pro Max zvážit `litersPerSecond` 2 (ladící hodnota v XML). Rozdílný přípravek: `pumpDrone` zahodí zbytek v dronu, který má jiný druh (Station 1801–1803) — platí per dron; pokud by dron 1 držel hnojivo a hlavní nádrž se mezitím přepnula na herbicid, dron 2 plní herbicid a pokrytí by kmitalo. Pravidlo: **start dávky dronu `k` vyžaduje, aby jeho `droneFillType` byl týž jako druh v `getFillSource`** (dnes zajišťuje `pumpDrone`; při `n = 2` doplnit kontrolu v `startNextBatch` s chybou `STATUS_TRAILER_EMPTY` → raději nový `STATUS_PRODUCT_MIX = 11`; `STATUS_NUM_BITS = 4` stačí, použito je 0..10).

### 3.3 Fond baterií a nabíječka

- `numBatterySlots` z XML `power#slots` (výchozí 5 = Car/Mini beze změny, Max 8). Nahradit `BATTERY_SLOTS` v Station 652, 780, 1904–1909, Service 57–70, 139, 149, 194, 197 a savegame (780). `batterySlotBits = ceil(log2(numBatterySlots + 1))` místo `BATTERY_SLOT_BITS = 3` (68): pro 8 slotů 4 bity.
- `battery = { charge, slot, drone }`; `slot == 0` znamená „v dronu `drone`“ (výchozí 1). `d.droneBattery = k` zůstává index v `spec.batteries` per dron. `readState` (3374–3379) nastaví `droneBattery` dronu podle `battery.drone`.
- **Zámek nabíječky se nezavádí.** Výměna dronu je atomická v jednom snímku serveru (`swapBattery`: `unloadDroneBattery` + `getBestSlottedBattery` + `loadDroneBattery`); druhý dron si vezme nejlepší z toho, co zbylo, nebo čeká (`swapPending`, `waitingForCharge`). Dvě odevzdané baterie dostanou rozdílné volné sloty, protože `unloadDroneBattery` zapisuje `battery.slot` hned (Station 1939) a `getFreeBatterySlot` ho při druhém volání už vidí. Animace přenosu jsou nezávislé po baterii (`batteryMoves[k]`); jediná vazba — zpoždění příchozí baterie za vycházející (`startBatteryMove` 325–334) — jen o ≤ 1,4 s zdržuje, bez kolize.
- **Skládání vleku:** `updateBatteryPlacement` (1983) odevzdá baterii každého dronu při `unfold < 1`. Vizuál (`updateServiceVisuals` 187–211) musí pro každou baterii s `slot == 0 and batteryStowed` brát **další** volný slot, ne stále `freeSlot` první (opravit, jinak se dvě baterie posadí do téhož slotu a kontrolky LED se slijí).
- Najíždění dronu 1 má při rozložení vleku přednost (v `forEach` pořadí 1, 2): `updateBatteryPlacement` mu dá nejlépe nabitou; dron 2 dostane další. Při jediné baterii létá jen dron 1 (`activeDrones = min(nastavení, numDrones, #batteries)`).
- Centrála (`updatePower` 2019): beze změny; nafta úměrně počtu nabíjených (`dieselPerSecond · charging`), fond se nabíjí najednou.

### 3.4 Zvuk a vizuál vozidla

`isMixing` je per-drone (kdo právě míchá, ten drží hadici); zvuk mixéru: `anyDrone(self, "isMixing")`. `generatorRunning`/`generatorEnabled` vozidlové. Každý dron má vlastní vzorek rotorů (`<drone slot="2"><sounds><rotor … linkNode="Drone2_A_Tilt"/>`), `SprayDroneStation.SOUND_*` platí. Hotspot: jeden `PlaceableHotspot` per dron (vzor `SprayDroneHotspot.create(spec)`, ikona `mapDrone.dds`; druhému lze popisek „2“).

### 3.5 Předávání mezi drony

- **Náplň** mezi drony nejde přímo, jen přes nádrž vleku: `TRANSFER_DRAIN_DRONE` (dron → nádrž, `Alt+1`) a plnění (nádrž → dron). `Alt+1` vypustí dron s větší náplní, který to umožňuje (`getCanTransfer`); opakované stisknutí = stop. Událost nese `droneIndex` (kap. 4.2). `SprayDroneStation.TRANSFER_TO_PALLET` (IBC) beze změny.
- **Baterie** jen přes nabíječku (jeden fond).
- **Práce** se „předává“ přepočtem rozdělení (kap. 2.3): vrátí-li se dron 2 dřív (RETURN_HOME, chyba), jeho nepostříkané legy jsou v dalším rozdělení dronu 1.

---

## 4. Síť a savegame

### 4.1 `writeState` / `readState`

Dnešní `writeState` (Station 3325–3355) zapisuje: `state, status, fieldId, missionActive, droneFillLevel, droneFillType, battery, sprayEffectsActive, isPumping, isMixing, isSwapping, waitingForCharge, generatorRunning, generatorEnabled, baterie (charge + slot), transferMode, Toolbox, poloha`. **Pro `numDrones == 1` zůstane tento blok bajt po bajtu stejný** (`slot` s `batterySlotBits`, což je pro 5 slotů dál 3). Pro `numDrones > 1` se **za něj přilepí**:

| co | bitů | pozn. |
|---|---|---|
| blok dronu 2: `state` (2), `status` (4), `missionActive` (1), `droneFillLevel` (f32), `droneFillType` (`FillTypeManager.SEND_NUM_BITS`), `battery` (f32), `sprayEffectsActive`, `isPumping`, `isMixing`, `isSwapping`, `waitingForCharge` (5×1), poloha: bool `not isLinked` + 4× f32 (`x,y,z,yaw`) | ≈ 225 | zapisuje `runAs(self, 2, writeDroneBlock)` |
| pro každou baterii se `slot == 0`: `battery.drone − 1` | 1 | |
| `hoseWanted` | 2 | |
| `transferDrone` | 2 | |

`readState` čte tentýž pořadím; `readDroneBlock` volá `runAs(self, 2, …)` a používá `detachDrone/attachDrone`, `netTarget`, `snap` jako dnes pro dron 1. Dirty flagy: **jeden** `dirtyFlag` (kap. 1.5) — blok dronu 2 se píše společně; zvýšení přenosu ≈ 28 B / snímek letu. Stávající přenos zahrnuje i celý Toolbox v každém dirty snímku (15 slotů, ≈ 80 B); případné rozdělení na `dirtyFlag` (vozidlo) a `droneDirtyFlag` je nepovinné zlepšení (etapa 8), v1 ne.

`onWriteStream`/`onReadStream` (3421/3436) posílají totéž + plochy, nastavení (nové `activeDrones`), pokrytí; `onWriteUpdateStream/onReadUpdateStream` beze změny struktury (`writeBool(dirty) + writeState`, `writeBool(coverageDirty) + coverage`).

### 4.2 Události

| událost | změna |
|---|---|
| `SprayDroneCommandEvent` (`NUM_BITS = 3`, příkazy 1..5) | + `streamWriteUIntN(streamId, droneIndex, 2)` (0 = všechny, 1, 2); `new(vehicle, command, fieldId, droneIndex)`; `run` volá `sprayDroneCommand(cmd, fieldId, true, droneIndex)`; `sendEvent(vehicle, command, fieldId, noEventSend, droneIndex)` |
| `SprayDroneServiceEvent` (`NUM_BITS = 2`) | + `droneIndex` (2 bity) pro `TRANSFER_DRAIN_DRONE`; `setSprayDroneTransfer(mode, noEventSend, droneIndex)` |
| `SprayDroneSettingsEvent` | `writeSettings/readSettings` + 6. hodnota `activeDrones` (UInt8) — vždy zapsat, jednodronový vlek ji ignoruje |
| `SprayDroneAreaEvent`, `SprayDroneToolboxEvent` | beze změny |

Příkazy zůstávají serverem ověřené: `START(droneIndex)` projde jen pro dron, který `hasDrone`, má baterii (nebo ji může dostat) a není `missionActive`; `droneIndex == 0` startuje všechny dostupné (max `activeDrones`).

### 4.3 Savegame

Čtení/psaní v `onLoad` (752–818) a `saveToXMLFile` (831–869). **Staré atributy = dron 1, bez změny:**

| cesta | nové / beze změny |
|---|---|
| `#fieldId`, `#generatorEnabled`, `#coverage`, `.flightSettings#…`, `.flightArea(?)…`, `.toolbox…` | beze změny |
| `#missionActive`, `#droneFillLevel`, `#droneFillType` | dron 1 (beze změny) |
| `.drone2#missionActive`, `.drone2#droneFillLevel`, `.drone2#droneFillType` | **nové**, jen pro `numDrones > 1`; čtení s výchozími `false/0/UNKNOWN` |
| `.battery(?)#level`, `#slot` | beze změny; `#slot` 0..`numBatterySlots` |
| `.battery(?)#drone` | **nové**, INT, výchozí 1, platí jen při `#slot == 0` |
| `.flightSettings#activeDrones` | **nové**, INT, výchozí `numDrones` |

Registrace (`initSpecialization`, 338–357) pro všechny nové cesty (`savegame:register`). Načítání: `battery(?)#slot == 0` se přiřadí dronu `#drone`, má-li `hasDrone` a ještě nemá `droneBattery` (existující logika 777–782 pro `drone` k); jinak do volného slotu. Starý soubor (Car/Mini s 5 bateriemi) se načte jako dnes; soubor s dronem 2 načtený do vozidla s jedním dronem (konfigurace „bez druhého dronu“ v budoucnu) ignoruje blok `drone2` a baterie z `#drone == 2` uloží do volných slotů. Po načtení `missionActive` obou dronů: `state = SERVICING`, `serviceTimer = RESUME_AFTER_LOAD_TIME` (813–817) pro každý; obnovu hadice a čerpadla řeší arbitr.

---

## 5. XML kontrakt

### 5.1 Princip

**Beze změny pro jednodronové vleky.** Nové atributy a bloky jsou nepovinné, žádný nový povinný uzel. `numDrones` se zjistí z XML: `numDrones = 2` jen když pro vybranou variantu existuje blok `slot="2"` **a** v i3d existuje `<prefix2>Root`; jinak 1. Car a Mini žádný `slot="2"` blok nemají → `numDrones = 1`, kód běží jako dnes.

Zamítnuté alternativy: `<sprayDrone2>` (duplikuje celý blok společných parametrů a vyžaduje ho celý znovu registrovat a načítat) a `<drone prefix="…">` bez `slot` (nelze rozlišit „druhý dron téže varianty“ od „druhé varianty“).

### 5.2 Pojmenování uzlů

| co | dron 1 (beze změny) | dron 2 |
|---|---|---|
| prefix varianty S / M / L | `Drone_S_`, `Drone_A_`, `Drone_L_` | `Drone2_S_`, `Drone2_A_`, `Drone2_L_` |
| uzly dronu (přípony) | `Root`, `Tilt`, `ArmPivot_1..4`, `Arm_1`, `Rotor_<i>Top/Bottom`, `Blade_<i><Top/Bottom><0/1>` (+ `_Tip`), `FillPort`, `BatterySlot`, `Clamp_1..4`, `ClampHinge_1..4`, `SprayNozzle_k`, `Led_1..4`, `LedLight_1..4` | totéž s prefixem dronu 2 |
| animace `foldLadder` | `…ClampHinge_i` dronu 1 (`CLAMP_PARTS`) | `Drone2_*ClampHinge_i` (už v exportu) |
| konfigurace `objectChange` | `Drone_A_Root`, `Drone_A_Clamp_1..4` | `Drone2_A_Root`, `Drone2_A_Clamp_1..4` (už v šabloně) |
| fond baterií | `battery1..8` (+ `battery<i>S/M/L`), `batterySlotDeck1..8`, `batteryCharger` | společný |
| LED nabíječky | `Charger_Led_<k>_<n>`, k = 1..8, n = 0..3 | společné |
| hadice | `fillHoseCoil`, `fillHoseStart`, `fillHoseLay1..8` (Max jich má 5), `fillHoseSeg1..96`, `fillHoseNozzle`, `fillHoseParkPos` | **jedna** sada; per dron jen `<prefix>FillPort` a `hoseVia` v bloku |
| společné | `generatorExhaust`, `generatorSoundNode`, `mixerSoundNode`, `dieselNeckNode`, `concentrateNeckNode`, `toolbox*`, `ladderTrigger`, `exitPoint`, `outdoorCamera`… | beze změny |

Uzly se hledají přes `getMappedNode(self, prefix .. "Root")` (Service 4); kontrola chybějících uzlů (existující logování při `DEBUG_POWER`, Service 110–127) se rozšíří na oba drony.

### 5.3 Atributy a bloky v `vehicle.sprayDrone`

```xml
<sprayDrone fillUnitIndex="1" … layerGap="6">                 <!-- layerGap nepovinné, výchozí 6 (m) -->
    <sprayDroneConfigurations> … Drone2_*_Root / Clamp_i v objectChange (už je) … </sprayDroneConfigurations>
    <sprayDroneBatteryConfigurations>
        <sprayDroneBatteryConfiguration name="0" count="0" … />
        … count 1..8; 8 se použije jen s <power slots="8"> …
    </sprayDroneBatteryConfigurations>
    <power dieselFillUnitIndex="2" slots="8" batteries="4" chargeMinutes="10" dieselPerHour="2.2" readyLevel="0.95" swapTime="5">
        <exhaust …/>
    </power>

    <drone name="M" prefix="Drone_A_" tankCapacity="40" … hoseVia="0.17 0.155 0.32"> …stávající děti… </drone>   <!-- slot 1, beze změny -->

    <!-- NOVÉ: dron 2 téže varianty. Parametry (tankCapacity, workWidth, …) se IGNORUJÍ a berou se ze slotu 1; platí jen prefix, hoseVia a děti -->
    <drone name="M" slot="2" prefix="Drone2_A_" hoseVia="0.17 0.155 0.32">
        <sounds><rotor file="sounds/droneRotorLoop.ogg" linkNode="Drone2_A_Tilt" innerRadius="8" outerRadius="120" fadeOut="300"> … </rotor></sounds>
        <effects nozzleY="-0.11">
            <effectNode effectClass="ParticleEffect" filename="effects/sprayMist.i3d" node="0|1" linkNode="Drone2_A_Tilt" … /> ×4
        </effects>
        {{DRONE_PARTS_M2}}      <!-- tilt, foldPart, propSource, propBlade, rotor, navLight s prefixem Drone2_A_ -->
    </drone>
    <!-- totéž pro S (Drone2_S_) a L (Drone2_L_) -->
</sprayDrone>
```

Schéma (`initSpecialization`): `drone(?)#slot` (INT, výchozí 1), `power#slots` (INT, výchozí 5, 5..8), `#layerGap` (FLOAT, výchozí 6); popis `#batteries`/`#count` „0..počet slotů“. Stávající `registerDronePartPaths(schema, droneKey)` už registruje děti pro `drone(?)`, takže blok slot 2 další registraci nepotřebuje.

Načítání (`loadDroneVariant`): `xml:iterate(key .. ".drone")` zařadí blok s `slot ~= 2` do `spec.variants` jako dnes a blok s `slot == 2` přiřadí k variantě téhož `name` (`variant.key2`, `variant.prefix2 = #prefix or ("Drone2_" .. name .. "_")`). Pro slot 2 kontext dronu 2 nastaví `droneKey = variant.key2`, `dronePrefix = variant.prefix2`, `node = <prefix2>Root` a ostatní jako dnes (`createStandInRoot` pro chybějící kořen).

Změny v exportu (`blender/templates/sprayDroneTrailerMax.xml.in`, `export_max_mod.py`; mimo kód módu):
1. v šabloně doplnit tři bloky `<drone slot="2" …>` s `{{DRONE_PARTS_S2|M2|L2}}` (hodnoty už generuje `write_vehicle_xml`), `sounds`, `effects` s `linkNode="Drone2_…_Tilt"`;
2. `sprayDroneBatteryConfigurations` rozšířit na 0..8 a `power#slots="8"`, `batteries="4"` (nebo 3);
3. `BATTERY_HIDDEN` (`export_max_mod.py:47–48`) skrývá `battery6M..8M`; skript je zobrazí (`applyBatteryMeshes`, Service 26), skrývání lze po etapě 2 vypustit;
4. ověření (skript `tools/check_drone_nodes.py`): pro každý `prefix` / `prefix2` z XML musí existovat v `<i3dMappings>` `Root`, `Tilt`, `FillPort`, `BatterySlot`, `Clamp_1..4`; pro každou šachtu `batterySlotDeck<i>` a `battery<i>`.

### 5.4 Kontroly při načtení (`loadDrone` pro slot 2, jen varování)

- `dist(home1, home2) ≥ 2 · droneRadius + 0,8` (rozteč 4,25 m vyhovuje i pro L: 3,3 + 0,8 = 4,1 m);
- `checkHoseReach(self, 1)` a `(self, 2)` (kap. 3.1);
- `FillPort` a `BatterySlot` existují pro oba;
- žádný `Drone2_*` kořen bez bloku `slot="2"` a naopak.

---

## 6. Plánovač (`gui/SprayDronePlannerScreen.lua`)

Jedno otevření, jedno pole, jedna letová plocha; plánovač dál drží `self.vehicle`. Změny:

| místo (řádek) | změna |
|---|---|
| `update` (213): `refreshRoutePreview(self.vehicle, dt)` | `SprayDroneStation.refreshRoutePreviewAll(vehicle, dt)`: přepočet obou dronů v jednom volání (kap. 2.7); `startButton:setDisabled(… or not getCanStart …)` = ani jeden dron nemůže startovat; `returnButton` = některý letí / má misi |
| `updateFields` (281), `getFieldAllowed` | kontext dronu 1 (rozsah z domova dronu 1) |
| `initMapView` (137) | `spec.range` dronu 1 |
| `onDrawPostIngameMap` (557–603): `spec.drawLegs`, `routeInfo.unplanned`, `routeInfo.turns` | smyčka přes drony (`forEach`), druhá paleta `SprayDroneStation.BATCH_COLORS_2` (tyrkys, zelená, bílá, růžová — odlišné od oranžové, fialové, modré, žluté); čáry dronu 2 mají „2“ u prvního legu (`renderText`); `unplanned` červeně z obou |
| `onDrawPostIngameMapHotspots` (605–619) | ikona vleku; ikona `mapDrone` pro **každý** letící dron (`not spec.isLinked and spec.node ~= nil`) s popiskem 1/2 |
| `drawPanel` (724–861): jeden řádek dronu (739–740) | smyčka: `Dron k: stav · nádrž · baterie`; „Baterie / nabíječka / centrála“ jednou; `sdt_planner_drone` (řádek 744) jednou (varianta je společná) |
| souhrn (780–827): `getRouteSummary` | `getRouteSummaryAll`: per dron `numBatches`, `minutes`, `areaHa`, `liters`; součty: plocha, litry (proti vleku + dronům), nafta, výměny baterií; **čas = max** (+ dolní odhad z čerpadla, 2.7); řádek výšky přeletu pro dron 2 „+ 6 m“ |
| `drawSettings` (649–696) | nový řádek `activeDrones` („Drony v misi: 1 / 2“; `SETTINGS` dostane položku `{ key = "activeDrones", min = 1, max = 2, text = "sdt_setting_activeDrones", minDrones = 2 }`); `drawSettings` a `handleSettingsMouse` přeskočí položky s `minDrones > spec.numDrones` (`settingRects` se plní jen pro viditelné) |
| `onClickStart` (427) | `startFlight(vehicle)` → `sprayDroneCommand(START, fieldId, …, 0)` všechny aktivní |
| `onClickReturn` (439) | `RETURN_HOME` s `droneIndex = 0` |
| `onClickResetField`, `onClickDeleteArea`, `commitDraft` | beze změny |
| legenda (`sdt_planner_legend`) | doplnit „2. dron: studené barvy“ |

Překlady (cs/en/de): `sdt_setting_activeDrones`, `sdt_hud_drone1/2` (řádek stavu per dron), `sdt_state_waitHose` („čeká na hadici“), `sdt_planner_dronesTotal`, `sdt_planner_layerNote`, `sdt_status_productMix`, `sdt_warning_dronePadSpacing`, `sdt_warning_noSecondBattery`.

Klávesy (`modDesc.xml`) beze změny: `Alt+8` startuje všechny aktivní, `Alt+0` vrací všechny, `Alt+1` vypouští dron s větší náplní.

---

## 7. Etapy, odhad, ověřování

### 7.1 Etapy

Odhad v pracovních dnech programátora včetně kontroly čtením. Každá etapa končí stavem, který je ověřitelný bez hry (kap. 7.3).

| E | obsah | den | ≈ řádků Lua | ověření (bez hry) | ve hře (až bude možné) |
|---|---|---|---|---|---|
| 0 | `scripts/SprayDroneFields.lua` (seznamy z kap. 1.5), `tools/audit_spec_fields.py`, `tools/test_drone_view.py` | 0,5 | 60 + 150 py | audit projde na stávajícím kódu (188 polí, žádné v obou seznamech) | — |
| 1 | `SprayDroneDrones.lua` (kap. 1.3), `spec.numDrones/drones` pro 1 dron, rozdělení `onUpdate` na `updateDroneVisual` / `updateVehicleVisual` / `updateDroneLogic` s `forEach`, `numBatterySlots` místo `BATTERY_SLOTS` (hodnota 5), `battery.drone` (výchozí 1), `Debug.chargeAll`, `Sound` `anyDrone`. **Bez změny chování.** | 2 | 250 | audit; `lua_check.py`; kontrola čtením, že `forEach` pro `numDrones == 1` nikdy nepřepíná; diff `writeState` prázdný | Car i Mini: let, servis, uložení — shodně s dneškem |
| 2 | druhý dron staticky: XML `slot`, `loadDrone` pro slot 2 (uzly, vizuál, zvuk, efekt, fold, LED), `numBatterySlots` 8, `batterySlotBits`, `hose.ports/vias`, cíl hadice (`hoseWanted`, bez arbitra pevně = dron s `SERVICING`), `freeSlot` sekvenčně, `writeState` blok dronu 2, savegame `drone2`/`battery#drone`, HUD/`getFillLevelInformation`, šablona Max (bloky slot 2) | 3 | 350 | audit; `check_drone_nodes.py`; `validate_mod.py`; lupa test pohledu | Max: oba drony vidět, rozkládají se, baterie přeskakují, hadice dosáhne na obě hrdla |
| 3 | arbitr hadice a čerpadla (`SprayDroneArbiter.lua`, čistá funkce), `pumpDrone` brána, `waiting`, `transferDrone`, drain s indexem, události (Command/Service/Settings) | 2 | 200 | `tools/test_arbiter.py` (stavový automat: R1–R5, FIFO, žádný hladovějící, `waiting` ≠ konec servisu) | plnění obou dronů ze Servisu po sobě |
| 4 | let dronu 2: `START/RETURN_HOME(droneIndex)`, per-drone `missionActive/status`, `updateFlight` brána `hose.drone == k`, brána plošiny, vrstva `layerOffset` v `getFlightParams`/`makeTransit`; **dron 2 sám celé pole** (`activeDrones = 1` s volbou dronu v debug.xml) | 1,5 | 150 | audit; čtení | dron 2 vzlétne, nastříká pole, přistane |
| 5 | dělení práce: `buildAllLegs`, `SprayDroneRoute.splitLegs` + `reverse`, rezervace (`getReservedSegments`, `reserved` v `buildLegs`/úvratích), `endMission`/`FIELD_DONE` logika, `minSplit` | 2,5 | 300 | `tools/test_split.py` (lupa: součet délek obou seznamů = původní, žádný překryv, rezervace vyloučí, obrácení legů, `minSplit`, úvratě, ostrovy; vyvažování konverguje v simulaci „dva drony postupují stejnou rychlostí“) | oba drony na jednom poli, žádný překryv, společné pokrytí |
| 6 | plánovač (kap. 6), `getRouteSummaryAll`, `updateRoutePreview` pro oba, fond/nafta v náhledu, překlady | 2 | 250 | `lua_check`; čtení | panel a mapa pro dva drony |
| 7 | dynamická pojistka „dron v cestě“ (`SEPARATION_GUARD`), `avoidHeight` podmínka, timeout konfliktu | 2 | 200 | `test_split.py` neovlivněn; geometrický test funkce `getDroneConflict` (čistá funkce `SprayDroneRoute.getPathConflict(path, other, sepH, sepV)`) v lupa | křížení trajektorií při přistání obou |
| 8 | doladění: rozdělení `dirtyFlag`, výkon (rozložení přepočtu), `Alt+1` volba dronu, dokumentace `docs/DRON.md`, vypuštění `BATTERY_HIDDEN` | 1 | 100 | — | MP |

Celkem ≈ 14,5 dne, rezerva 10 % = **≈ 16 dnů**, ≈ 1 300 řádků Lua (+ ~150 py, ~120 řádků XML/šablon).

### 7.2 Co je u které etapy riziko

- **E1** je největší jednorázový zásah do `onUpdate` a `updateDroneParts`; i když chování pro 1 dron nemění, jde o nejčastěji vykonávaný kód. Pravidlo: v E1 se **nic nepřidává** (žádná nová funkce kromě rámce), diff se čte řádek po řádku proti původnímu.
- **E2** — `loadDrone` pro slot 2 je kopie části `onLoad`: raději extrahovat do funkce a volat ji pro oba kontexty, ne duplikovat.
- **E3, E5** — logika stavů (`waiting`, `FIELD_DONE`) je nejnáchylnější na tiché chyby (kap. 3.1, 2.6).

### 7.3 Ověřování bez hry

1. **`tools/audit_spec_fields.py`** (statické): načte `SprayDroneFields.lua`; projde `scripts/**/*.lua` (`spec.<jméno>`, `getSpec(self).<jméno>`); **selže**, když (a) jméno není v žádném seznamu, (b) je v obou, (c) seznam obsahuje jméno, které se nikde nepoužívá. Vypíše tabulku funkce × {V, D, obojí} — to je soupis „smíšených“ funkcí z kap. 1.6 k ruční kontrole a po E1 stav, kdy žádná vozidlová funkce mimo těch označených V→D v kap. 1.6 nesahá na D pole.
2. **`tools/test_drone_view.py`** (lupa, bez herních API): pohled čte sdílená pole z `spec`, zapisuje je do `spec`, per-drone pole drží vlastní, neinicializované per-drone pole vrací `nil`, `runAs` vnořený a po chybě obnoví `self[SPEC_NAME]`, `drones[1] == spec`.
3. **`tools/test_split.py`** (lupa, vzor `tools/test_headlands.py`: mock `MathUtil`, `CollisionFlag`, `getIsWorkable`): kap. 7.1 E5.
4. **`tools/test_arbiter.py`**: `SprayDroneArbiter.step(state, inputs, dt)` je čistá funkce (stav `hoseWanted`, `hoseT`, `arrival[k]`, `wants[k]`): R1–R5, přepnutí vyžaduje `hoseT = 0`, FIFO, `DRAIN` předbíhá jen při přidělování.
5. `tools/lua_check.py` (syntaxe) a `tools/validate_mod.py` (schéma; `<sprayDrone>` sekce se mu neověřuje, to je v pořádku) po každé etapě; `tools/check_drone_nodes.py` (kap. 5.3).
6. Ladící příkazy do `SprayDroneDebug.runCommand` (až půjde zkoušet): `dronesStatus` (log obou stavů), `forceDrone2` (`activeDrones = 1` s dronem 2), `swapDroneBatteries`.

---

## 8. Rizika, pasti a otevřené otázky

### 8.1 Pasti, na které se v kódu snadno narazí

1. **`nil + 0.5` při načtení** (Station 623–625): `spec[setting.key]` pro novou položku `SETTINGS` musí být inicializované dřív.
2. **Konec servisu při čekání na hadici** (kap. 3.1) — jinak mise skončí „nádrž prázdná“.
3. **`#legs == 0` není „pole hotové“** (kap. 2.6) — jinak druhý dron smaže pokrytí a pole se letí znovu.
4. **`setState` nuluje `isMixing/isPumping/…`** jen vlastního dronu (kontext), nikdy sdílené.
5. **`routeDirty` všem dronům** při změně pole, plochy, nastavení, pokrytí (`clearCoverage`), `readStream`; jinak druhý dron plánuje podle staré trasy.
6. **`getFlightParams` closures** — viz kap. 1.2 bod 3.
7. **`slot == 0` ambivalentní** (dron 1 / dron 2): vždy číst `battery.drone`; `readState` nastavuje `droneBattery` podle něj.
8. **Skládání baterií do téhož slotu** (Service 187–196).
9. **Ukazatel naplnění (`getFillLevelInformation`)**: vanilla kreslí nejvýš 5 řádků; po sloučení nádrží dronů je řádků nafta, baterie, hlavní, koncentrát, drony = 5.
10. **`hoseT > 0` brání vzletu** (Station 2395): po změně jen pro dron s hadicí.
11. **Stejný přípravek pro oba drony** (kap. 3.2): `markCovered` při změně druhu přepíše záznam (`getCoverage` vyžaduje shodu).
12. **`getHomePath` / koridor per dron**: domov dronu 2 musí ležet v tolerance plochy (6 m); jinak `NO_PATH_HOME` jen pro dron 2 (plánovač to musí ukázat per dron, ne jen z dronu 1).
13. **`table.insert(lay, getMappedNode(…))`** s `nil` (Max má 5 bodů `fillHoseLay`): nic nepřidá, hadice se staví z existujících (stávající chování, nesahat).
14. **Výkon:** přepočet náhledu je dnes 60–130 ms při změně (DRON.md „Na příště“ 5); dva drony = dvojnásobek, `buildAllLegs` je ale jedna (raycasty/hustotní mapy), druhý dron jen `splitIntoBatches`. Přepočet dronu 2 posunout o `ROUTE_REFRESH_TIME / 2` (2,5 s) a za letu nepočítat oba v témže snímku.
15. **Pad (Mini)** používá `getFoldAnimTime` a `spec.pad` jen v kontextu dronu 1; dron 2 nikdy `pad` nemá (`rawget` nil).

### 8.2 Rozhodnutí, která potřebuji od Pavla

1. Oba drony **téže varianty** (jedna konfigurace S / M / L), nebo možnost smíšené dvojice? Doporučuji tutéž (kap. 0 bod 2); smíšená dvojice by z V1 udělala ~30 per-drone polí a fond baterií by musel mít dva typy.
2. `Alt+8` startuje oba drony, `Alt+0` oba vrací; samostatné ovládání jen v plánovači (řádek „Drony v misi“)? Doporučuji ano.
3. Čerpadlo vleku Max: 1 l/s (stejně jako Car) nebo 2 l/s? Při 2 dronech a L (75 l) je čekání na hadici znatelné.
4. `LAYER_GAP` 6 m a `PAD_CLEAR` 8 m (kap. 2.5) — v pořádku, nebo chce Pavel ostřejší / volnější? Rozteč plošin 4,25 m je pro L těsná (3,3 m + 0,95 m rezervy); kdyby šla v Blenderu zvětšit na ≥ 5 m (např. `PAD_Y` ± 1,0), vzdušný režim se zjednoduší.
5. Dělení pole `dvoustranně od konců k prostředku` (kap. 2.2) nebo `každý dron samostatný pás od začátku` (odpadá `splitLegs`, ale dron 2 by se dostal jen k vlastní polovině a vyvažování by bylo statické)? Doporučuji dvoustranné.
6. Stejný přípravek pro oba drony (kap. 3.2): akceptovat chybové hlášení při jejich smíšení, nebo automaticky vypustit náplň druhého dronu?
7. Savegame zpětná kompatibilita je zajištěna (kap. 4.3); jednosměrná (nový soubor do staré verze módu) se neřeší.

## 9. Rozhodnutí Pavla a skutečné uspořádání modelu (2026-10-04)

Odpovědi na otázky z 8.2 a změny oproti návrhu (platí nad kap. 1–8, kde se liší):

- **Obě drony stejná velikost** (jedna konfigurace S/M/L pro oba), žádná smíšená dvojice.
- **Jedno tlačítko startuje i vrací oba drony**: `Alt+8` (start) a `Alt+0` (návrat) platí pro oba.
- **Rozteč ploch 5 m** (středy ploch y = −1,15 a 3,85; paluba 7,5 m dlouhá), L se vejde.
- **Dělení pole dvoustranné** podle zbývající práce (jak navrženo v kap. 2).
- **Dvě hadice, žádná fronta na jednu**: každý dron má vlastní navíječ, řetěz 96 článků a koncovku. Uzly dronu 1 jsou beze změny
  (`fillHoseCoil/Start/Lay1-8/Seg1-96/Nozzle/ParkPos`), uzly dronu 2 mají `fillHoseB…` (`fillHoseBCoil`, `fillHoseBStart`,
  `fillHoseBLay1-8`, `fillHoseBSeg1-96`, `fillHoseBNozzle`, `fillHoseBParkPos`). Hadice je tedy per-drone stav; FIFO z kap. 3 odpadá
  (obě se mohou plnit současně, sdílí jen nádrž a čerpadlo — společný průtok `litersPerSecond` se mezi plnicí dělí).
- **Natočení dronů**: oba nosem ke středu paluby, přední dron (Drone_*) nosem dozadu (proti směru jízdy), zadní (Drone2_*) nosem
  dopředu. Plnicí hrdlo je na pravém boku trupu, takže přední dron má hrdlo na levé straně paluby a zadní na pravé; navíječ A stojí
  vlevo u přední plochy, navíječ B vpravo u zadní (bodově souměrně podle středu servisní zóny y = 1,35).
- **Nabíječka**: jedna, 8 šachet (`battery1..8`, `batterySlotDeck1..8`, `Charger_Led_k_n` k = 1..8), otočená o 90° u levého okraje
  paluby, víko `chargerLid` má zavřené natočení o 90° kolem svislé osy (`LID_CLOSED`) a otevírá se o 120° ven přes okraj.
- Výtlak čerpadla se dělí do dvou větví (`Pump_Discharge`, `Pump_DischargeB`) k otočným přívodům obou navíječů.
- Stage 1 (hotovo): model a export; Lua zatím obsluhuje jen dron 1 a hadici A, baterie 6–8 jsou v i3d skryté.
