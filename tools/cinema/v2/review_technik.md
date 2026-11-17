# Posudek technika proveditelnosti: scénář v2 (verze 1)

Role 2b podle `prompts/02_kontrola_scenare.md`. Posuzováno `scenar.md` (kap. 0–10).
**Metoda:** čtení zdrojů (`FS25_SprayDroneCinema/scripts/*.lua`, `SprayDroneDebug.lua`, `SprayDroneStation/Route/WaterHose/Mill/Hopper/Link.lua`, `gui/SprayDronePlannerScreen.lua`, `docs/DRON.md`, `davka_A/B/U.md`, vzorové scény). **Hru jsem nespouštěl a na `cinema_client` nic neposlal**, takže vše níže je „z kódu“, ne „ve hře ověřeno“. Kde je závěr jen odvozený, je to napsané.

## 0. Souhrn

91 záběrů celkem (mini 24, middle 24, max 33, spol 3, prod 7).

| stav | význam | počet |
|---|---|---|
| **A** | proveditelné hned (příkazy existují, stačí napsat scénu) | **48** |
| **A\*** | příkazy existují, ale záběr závisí na průzkumu místa u rybníka (O1) nebo na ověření ve hře | **29** (Middle 22, Max 7) |
| **B** | chybí příkaz dev módu (kap. 3) | **14** |
| **C** | nejde ani s novým příkazem | **0 celých záběrů**, ale **dva obsahy nejdou** (kap. 2: planner nekreslí přelety ani překážky, u `max-6.2`/`6.4` je potřeba opravit text) |

Pro 14 záběrů kategorie B je nutných šest příkazů (N2, N3, N4, N5, N6, N9), čtyři jsou silně doporučené (N1, N7, N10, N11), dva volitelné (N8, N12), viz kap. 3. Největší riziko není kód, ale **místo u rybníka** (O1) a **izolace scén** (Z1, O9).

Společné předpoklady, které v tabulce značím zkratkou:

| zkr. | předpoklad |
|---|---|
| **I** | izolace: cizí soupravy zaparkované mimo dohled (dnes ručně přes `placeSet` na parkoviště, s N1 jedním příkazem), cizí rekvizity smazané (`removeVehicle all=true`, `ui relayRemove`) |
| **S** | po `placeSet` a `fold unfold wait` pauza ~6 s a `groundCheck` (u SIL `maxTilt 9`) před záznamem |
| **T** | `setTime lock=true` + `setWeather SUN` + `setFog reset` a před akcí s dronem `play command=windOff` (vítr může misi přerušit, `checkWeather`) |
| **R** | reset stavu: `resetField` (paměť pokrytí; bez něj druhý take jen dopostřikuje), `droneSet battery= tank=`, `setTank` pro hlavní nádrž a koncentrát, `generator on=false fuel=10`, `dbg whDrop` |

## 1. Jak hra a mód fungují, z čeho jsem vycházel (jen to podstatné)

- **Dev mód** dostává příkazy souborem (`cmd.xml`, dotaz každých 250 ms, klient čeká na `ack`). Latence jednoho příkazu je 0,05–0,3 s s jitterem; každý další příkaz ji přidá. Lua moduly jdou nahrát za běhu (`cinema_client.reload_live`), takže nové příkazy se dají přidat bez restartu hry (zip 0.1.5 v Mods je zastaralý, `build.py` až po vypnutí hry).
- **`eval`** spustí Lua soubor (`source`), takže cokoliv, co chybí, jde jednorázově obejít souborem v `tmp/` (průzkum, jednorázové úpravy). Je to cesta pro průzkum rybníka (kap. 5).
- **Dron letí kinematicky z `dt` snímku** (`SprayDroneStation.updateFlight`: `pos += dir * speed * dt`, rychlost s konstantním zrychlením). Dráha v prostoru je tedy deterministická a čas letu nezávisí na fps (hra neběží zpomaleně). Nedeterministické jsou jen: okamžik startu příkazu (jitter), podmínka roztočení rotorů, čekání na plošinu (`getIsOtherDroneNearPad`), pojistka proti překážce (`getIsPathBlocked`, raycast), vítr (`checkWeather`) a stav z minulého takeu (pokrytí pole, baterie, nádrž).
- **Rozložený vlek je kinematický** (`updateFreeze`), takže po rozložení se nehýbe a dron nehlásí „vlek se pohnul“.
- **Hadice patří vozidlu, které je vlastní** (výstupní hadice pumpy je v `pump.hoses[2]`; obsazenost ventilu vleku se počítá dynamicky `isPortOccupied` a smazaná vozidla ignoruje). Smazání pumpy tedy hadice nenechá viset a ventil se uvolní.

## 2. Tabulka záběr → stav → co je potřeba

Značení: N1–N12 jsou chybějící příkazy z kap. 3. „camPath `at=`“ znamená kameru vázanou na uzel vozidla (`at="mini"`, `"max:drone1"`), `tat=` totéž pro cíl.
Pohyby: PAN/TILT/TRK/JIB/NAJ/ODJ/TOP/STAT = `camPath` (cíl `tat=` na vleku dělá sledující švenk), ORB = `camOrbit` (kladný přírůstek úhlu `angle0→angle1` je **proti** směru hodin při pohledu shora s polohou sever nahoře, CW tedy znamená `angle1 < angle0`), FOL = `camFollow target=<vlek>:drone<k>`, MAPA± = `ui plannerView`/`plannerField pan= zoom=`.

### 2.1 Film `mini` (vše SIL / CESTA / DVŮR, známé souřadnice z `b02`–`b04`, `c55`)

| ID | stav | co je potřeba |
|---|---|---|
| mini-1.1 | A | `driveTo kmh=36 mode=line`, `camPath` tele (fov 12–18); rozjezd aspoň 60 m před viditelným úsekem; I, S (SIL maxTilt 9) |
| mini-2.1 | A | stejná jízda, kamera pevná, cíl `tat="mini"` (sama sleduje) |
| mini-3.1 | A | `driveTo` po CESTĚ, `camPath at="mini"` s bočním odsazením (TRK); vzor `b03_gravel` |
| mini-3.2 | A | `driveTo radius=` → stojí; brzdová světla svítí jen pokud je hra rozsvítí při brzdění AI (nejde vynutit, nepodmiňovat záběr) |
| mini-4.1 | A | `fold unfold wait` + `camOrbit target=mini`; animace 12 s (O11), střih jen na 10 s |
| mini-4.2 až 4.6 | A | stojící vlek, `camPath`; polohy nutno přepočítat z i3d souřadnic do souřadnic vleku (kamera `at` bere jen kořen vozidla, ne pojmenovaný uzel), doporučeno N11. 4.4: ověřit, že je víko truhly po rozložení otevřené |
| mini-5.1 | **B** | N5 (kanystr z police + idempotentní otevření bedny; `toolboxOpen` je přepínač) |
| mini-5.2 | A | `setTank conc EMPTY`, `canisterPour fill=herbicide` (vzor `c33`), hráč do 15 m (`playerTo force=true`) |
| mini-6.1 | A | displej svítí 10 min po vzniku vleku (`SCREEN_SLEEP_MS`), potom zhasne a rozsvítí se až při otevření plánovače: N10 (`screenWake`), jinak ověřit |
| mini-6.2 | A | `ui plannerOpen`, `plannerHover off`, `plannerField id=4 pan= zoom=` (vzor `u41`/`u42`); ikony cizích vozidel viz O9 (I nebo N8) |
| mini-6.3 | A | `ui plannerPage`, STAT |
| mini-7.1 | A | `startFlight field=4` (vybere pole a koupí ho), `camPath at="mini:drone1"` stoupá |
| mini-7.2 | A | `camFollow target=mini:drone1` |
| mini-7.3 | A | `camPath` TOP nad dronem (cíl o 0,5 m vedle, ať není degenerovaný pohled) |
| mini-7.4 | A | nejdřív kalibrační běh s `trace on` (logy `DRN`), potom pevná dráha kamery |
| mini-7.5 | A | `returnHome` (po zvolené době) + `waitDrone near`, STAT tele |
| mini-7.6 | A | `droneSet battery=0.2 tank=0`, `waitDrone servicing`, `camOrbit target=mini:drone1`; vzor `c55` (baterie 5 s, nádrž ~20 s) |
| mini-7.7 | A | **tentýž take** jako 7.6, jiná kamera (D) |
| mini-8.1 | A | `waitDrone parked`, `fold fold wait`, JIB-D |
| mini-8.2 | A | `lights vehicle=jd3650 mask=255`, `driveTo` |

### 2.2 Film `middle` (beaty 3–8 u rybníka, závisí na O1)

| ID | stav | co je potřeba |
|---|---|---|
| middle-1.1, 2.1 | A | jako mini-1.1/2.1 |
| middle-3.1 | A\* | `driveTo mode=line` jede **přímo**, ne po lesní cestě; potřeba přímý úsek ≥ 45 m bez stromů a s pevnou zemí k místu. Jinak nahradit krátkým průjezdem po otevřené trávě (pak C pro „lesní cestu“) |
| middle-3.2 | A\* | `placeSet` na rovné místo u vody, `driveTo radius`, ODJ; voda musí být v záběru (průzkum) |
| middle-4.1 | A\* | `nodeVis show=antennaLarge,gpsRtkBox,antennaBase` **před** `fold unfold wait` (vzor `b09`, O10), ORB |
| middle-4.2 až 4.5 | A\* | stojící vlek; N11 doporučeno |
| middle-4.6 | A\* | totéž, stožár: ověřit, že se při rozložení vysune a nestojí hned vysunutý (O10) |
| middle-5.1 | A\* | `dbgCmd toolboxFill`, `toolboxOpen` (přepínač!, proto N5), roleta |
| middle-5.2 | A\* | `canisterPour fill=fertilizer` |
| middle-6.1 | A\* | N10 |
| middle-6.2, 6.3 | A\* | pole musí ležet do dosahu rádia (450 m, `spec.maxRange`) od místa u rybníka; pole 83 je u řeky (440,−230), ne nutně u rybníka. Kdyby žádné pole v dosahu nebylo, použít relé (`ui relaySpawn`, jedna tyč do 450 m od vleku) |
| middle-7.1 | A\* | start z horní plošiny; **volný vertikální sloupec** nad plošinou a v ose stoupání (pojistka `getIsPathBlocked` jinak mise skončí `STATUS_OBSTACLE`) |
| middle-7.2, 7.3 | A\* | FOL / TOP |
| middle-7.4 | A\* | pohled z dronu: **není potřeba Alt+9**. `camPath` s `at="middle:drone1"`, `full=1` (pozice i cíl v souřadnicích dronu, včetně náklonu); osu „dopředu“ uzlu dronu ověřit zkouškou. Záložně TRK (O8) |
| middle-7.5 | A\* | `returnHome` + `waitDrone near`, PAN-L |
| middle-7.6, 7.7 | A\* | jako mini-7.6/7.7 (jeden take, dvě kamery) |
| middle-8.1, 8.2 | A\* | `fold fold wait`, `driveTo` z místa u vody (opět přímý bezstromový odjezd) |

### 2.3 Film `max`

| ID | stav | co je potřeba |
|---|---|---|
| max-1.1, 2.1, 3.1, 3.2 | A | jako mini; MT655 + Max (~15 m) na SIL, sklon 6,4° (O25: `groundCheck maxTilt 9`, jinak ztráta času) |
| max-4.1 | A | vzor `c26_max_unfold` (dva drony se rozloží) |
| max-4.2 až 4.6 | A | N11 doporučeno; 4.6: kohout `limeValveLever` je v modelu |
| max-5.1 | **B** | N5 (kanystr nafty z police Maxu) |
| max-5.2 | A | `canisterPour fill=diesel` je v kódu (`toolbox.dieselNeckNode`); ověřit, že uzel existuje i na Maxu s vápennou konfigurací (O12) |
| max-5m.1 | A\* | `placeSet` Max, `fold unfold`, `spawnMod objects/pump/waterPump.xml diesel=10`, `moveVehicle` pumpy, `setTank main EMPTY`, `dbg whDrop`, `dbg whPond`, `dbg whOut`, `dbg pumpOn`; kap. 5 |
| max-5m.2 | A\* | sací koš (`inStrainerEnd`) pod hladinou, JIB-D; vodu a odlesk ověřit na místě |
| max-5m.3 + 5m.4 | A\* | **jeden souvislý take, jeden uzamčený rám**: v polovině `removeVehicle vehicle=waterPump all=true` (hadice zmizí s pumpou), `setTime lock=true`; střih na shodu dělá střih. Hadice nezůstane viset (kap. 1) |
| max-5m.5 | A\* | `spawnMod vehicles/sdtLimeMill/sdtLimeMill.xml`, `moveVehicle`; hadice vleku je 12 m, takže mlýnek ≤ 11 m od vápnové spojky (scénář říká 10 m, je to těsné, raději 7–8 m) |
| max-5m.6 | **B** | N6. **Pozor:** `bagLift` zvedá big bag nad **násypku** (`limeHopper`), ne nad mlýnek (kap. 4, nález F2) |
| max-5m.7 | A\* | `dbg whConnect<N>` (N = číslo vápnové spojky z `dbg whStatus`, v `c63c` to bylo 5) + `dbg whValve`; mlýnek do 12 m od spojky |
| max-5m.8 | A\* | `millDbg millFill`, `millOn` (vzor `c63c`); prach ani tok vápna vidět nejsou (O17) |
| max-6.1 | A | N10 (jako mini-6.1) |
| max-6.2 | A | pole 2 (`setField growth=cut`), `ui plannerField`; „Výška přeletu 20 m“ je ve kartě (potvrzeno `davka_U` 4.2). **Přelety a červené body překážek planner nekreslí** (kap. 4), scénář to tvrdí |
| max-6.3 | A | karta; 2 drony se v kartě ukážou |
| max-6.4 | **B** | N2 (`flightArea`). Zobrazí se **fialová plocha**, ne „bílé čárkované přelety po koridoru“ (kap. 4) |
| max-7.1 | A | `startFlight drone=0` (oba), druhý vzlétne s odstupem ~3 s (čekání na plošinu) |
| max-7.2 | **B** | N3 (formace přes zbylé řádky); bez něj drony stříkají vzdálené a opačně |
| max-7.3 | **B** | N3 (dvě sousední dráhy shora) |
| max-7.4 | A | funguje i bez formace |
| max-7.5 | A | `returnHome` obou, přistávají po sobě automaticky |
| max-7.6, 7.7 | A | jeden dron v servisu (`waitDrone servicing drone=1`), druhý stojí, jeden take / dvě kamery |
| max-8.1, 8.2 | A | `waitDrone parked` oba, `fold fold wait`, `lights`, `driveTo` |

### 2.4 `spol` a `prod`

| ID | stav | co je potřeba |
|---|---|---|
| spol-1 | A | tři `placeSet` (vzor `c02_three_wide`, `b08_finale`), `lights`, tři `startFlight` hned za sebou; kamera NAJ ukáže vzlet |
| spol-2, 3 | **B** | N4 (`droneHover`). Bez něj drony po ~5 s odletí z obrazu (`davka_A` bod 2), takže 16 s záběru s „drony nad vleky“ nejde. Záložně jen okno vzletu (každý take znovu: `returnHome` + `waitDrone parked`, ~60 s navíc) |
| prod-1, 2, 3, 5, 6, 7 | **B** | N9 (kanystry/pytel/big bag mimo vlek, klonování dronů a baterií), místo BET (O22) |
| prod-4 | A | `spawnMod` pumpy a násypky (`objects/hopper/limeHopper.xml`), štítky z fov 25–35 ověřit |

## 3. Chybějící příkazy: návrh implementace a náročnost

Náročnost: **nízká** (do cca 2 h včetně zkoušky), **střední** (půl dne), **vysoká** (den a víc nebo velká nejistota). Vše jen v `tools/cinema/FS25_SprayDroneCinema`, release mód se nemění; novinky jdou za běhu přes `reload_live`.

| č. | příkaz | co dělá a které funkce release módu volá | náročnost |
|---|---|---|---|
| **N1** | `isolate keep=<vlek> park=x,z [props=true]` | (1) ostatní soupravy SDT: `returnHome` + `waitDrone parked`, potom stejná logika jako `placeOnce` v `SprayDroneCinemaScene.lua` na parkoviště (`keepPlayer`, kola ověřit jednou u parkoviště), (2) odpojená cizí vozidla `C.teleport`, (3) rekvizity `removeVehicle all`: `waterPump`, `waterTrailer550`, `limeHopper`, `sdtLimeMill`, `limeBigBag`, `bigBag`, `relaypole`, kanystry (`FS25_SprayDroneTrailer.SprayDroneToolbox.getCanisterKind(v) ~= nil` → `v:delete()`). Parkoviště musí být mimo dohled a mimo okno plánovače (průzkum). Bez N1 jde totéž ručně ve scéně, N1 jen šetří chyby | střední |
| **N2** | `flightArea trailer field mode=strip\|points\|clear width=40 pts="x,z;x,z;..."` | `trailer:setSprayDroneFlightArea(fieldId, points)` (event + `markRouteDirty`). `strip`: pás šířky `width` od `SprayDroneStation.getHomePosition(trailer)` (zasunutý 8 m za vlek, ať je vlek uvnitř nebo ≤ 6 m od okraje, `HOME_TOLERANCE`) do pole (konec 15 m uvnitř polygonu `SprayDroneRoute.getPolygon(field)`). `points`: ručně navržený lomený obrys kolem stodoly. Po nastavení `SprayDroneStation.getCorridor(trailer) ~= nil` jako kontrola a log. **`clear` po natáčení**: plocha se ukládá do `vehicles.xml` při uložení hry. Volitelně `worldLines on` (nastaví `SprayDroneStation.showWorldLines`) pro letecký záběr s čarami | nízká |
| **N3** | `coverLines trailer field keep=k0,k1\|auto2` | obdoba `SprayDroneDebug.runCommand "coverField"`: `spec.coverage[fieldId] = entry` s řádky zcela pokrytými kromě `keep`, úvratě a ostrovy pokryté, potom `SprayDroneStation.markRouteDirty` a `raiseCoverage(trailer, true)`. Zbydou dva sousední řádky. Pole se dělí „dron 1 prefix, dron 2 zbytek pozpátku“ (`docs/DVA_DRONY_NAVRH.md` 2.2) a řádky se střídají (E, W), takže dron 2 poletí řádek 2 **stejným směrem** jako dron 1 řádek 1, rozteč řádků = `workWidth` (S 6 m). Odstup startu ~3 s zůstane (plošina). Před tím vždy `resetField`. Vyřeší O5 a `max-7.2/7.3` | nízká |
| **N4** | `droneHover trailer drone seconds` | obálka na `SprayDroneStation.updateFlight` (volá se přes tabulku, takže jde přepsat): dokud `g_time < until`, dron drží pozici (nevolat původní funkci, rotory se točí z `updateDroneParts`, baterie se nevybíjí). Pozor na kontext dronu (`runAs`, `docs/DVA_DRONY_NAVRH.md` 1.x), ověřit na dvou dronech. Po vypršení původní funkce pokračuje. Vyřeší `spol-2/3` a `davka_A` požadavek 2 | nízká až střední |
| **N5** | `toolboxSet trailer open=true\|false part=all fill=true` a `canisterPour ... from=box slot=n` | `FS25_SprayDroneTrailer.SprayDroneToolbox.setOpen(trailer, open, part)` jen když se stav liší (dnes `toolboxOpen` jen přepíná všechny části, dalším take se bedna zavře). `from=box`: první klíč kanystru ve světové poloze slotu `toolboxCanister<n>` (`trailer.i3dMappings`), vizuál slotu na dobu pohybu skrýt (`setVisibility`) a po konci vrátit, ať kanystr není dvakrát | nízká až střední |
| **N6** | `bagLift target=mill` (a vanilla big bag s hrubým vápnem) | zobecnit `findHopper()` v `bagLift`: cíl mlýnek, ústí = `exactFillRootNode` první fill unit mlýnku (`mill.spec_fillUnit.fillUnits[1]`), big bag z `data/objects/bigBag/lime/bigBag_lime.xml` (existuje v základní hře) s `FillType.LIME`; zbytek (kinematické vedení, `sdtEjectTime`, smazání po vyprázdnění) beze změny. Že se vanilla big bag nad `exactFillRootNode` mlýnku vyklopí sám jako u násypky (`c62`), je **neověřený předpoklad**. Záložně: celý 5m.6 přes násypku (`c62` ověřené) | střední |
| **N7** | `mark name` a `seq` | `mark` zapíše `C.log("MARK %s")` s `g_time` (kotva pro sesynchronizování klipů, kap. 6). `seq` provede seznam příkazů s časem relativně od startu uvnitř hry (`C.handlers[cmd](args)` z časovače v `C.frame`), takže odpadne jitter souborového dotazu (0,05–0,3 s na příkaz) | `mark` nízká, `seq` střední |
| **N8** | `hideHotspots keep=<vlek>` (volitelné) | skryje vanilla značky ostatních vozidel a značku dronů (`SprayDroneHotspot.getIsVisible`) na dobu záběrů s plánovačem. API `MapHotspot` jsem neověřil. Záložně I (parkoviště mimo okno mapy) | střední (nejisté API) |
| **N9** | sada pro `prod`: `spawnCanister kind=fertilizer\|herbicide\|diesel\|limebag x z yaw`, `spawnMod ... fill=<FILLTYPE> liters=`, `cloneNode` | kanystry a pytel: `SprayDroneToolbox.spawnCanister(<libovolný vlek SDT>, fillType, liters, cb, {x,y,z,yaw})` (pozice se zadává, vlek může stát jinde). Big bag: rozšířit `spawnMod` o naplnění. Drony S/M/L a baterie: `clone(node)` uzlu z `i3dMappings` (`Drone_S_Root`, `battery1S`…) a položení na podstavec; M a L existují jen u vleku s touto konfigurací (u Maxu `padDrone variant=M\|L`). Animace a materiály klonu jsou nejisté | střední (drony **vysoká**, nejisté) |
| **N10** | `screenWake trailer` | `SprayDroneDrones.getRoot(trailer).screenWakeTime = g_time` (jako `SprayDroneLink` řádek 686) | nízká |
| **N11** | kamera `at="max#chargerLid"` | `C.resolveNode`: za `#` hledat v `vehicle.i3dMappings[id]` (jako `nodeVis`); ušetří přepočet polohy ze zdrojů do souřadnic vleku u 15 detailových záběrů | nízká |
| **N12** | `droneDock trailer` (volitelné) | okamžité uložení dronu na plošinu mezi takey (šetří 45–90 s `returnHome`). Odvodit z `endMission`/`attachDrone`; riziko stavových polí. Bez něj stačí `returnHome` + `waitDrone parked` | střední |

Nepotřebné příkazy (původní podezření, nakonec stačí existující): pohled z dronu (kamera `at` s `full=1`), odebrání pumpy (`removeVehicle`), napojení mlýnku (`dbg whConnect<N>` + `whValve`), plnění big bagem do násypky (`bagLift`, ověřeno v `c62`).

## 4. Plánovač: co se dnes kreslí a co jde ukázat jako „letový koridor“

Čteno z `SprayDronePlannerScreen:onDrawPostIngameMap` a `docs/DRON.md` (od 2026-10-01):

| prvek | v plánovači (mapa) | ve světě (jen s `Alt+5`, ve výchozím stavu vypnuto) |
|---|---|---|
| obrysy polí, vybrané pole silně, bublina pod kurzorem | ano | zelený obrys vybraného |
| kruh dosahu rádia vleku a kruhy relé | ano | ano (`drawWorldSignal`) |
| řádky postřiku, barva podle dávky (`drawLegs`, jen úseky s `wp.spray`) | ano | ano |
| půlkruhy otoček mezi řádky (`routeInfo.turns`) | ano | ano |
| řádky, které se do plánu nevešly | červeně | – |
| **letová plocha** (polygon, kreslená klávesou X) | ano: fialová výplň a obrys | fialová čára 1 m nad terénem |
| **přelety vlek ↔ pole** (`routeInfo.transits`) | **ne** | ano: bílé, ve výšce přeletu, jen první dvě dávky (`WORLD_TRANSITS`) |
| červené body překážek s výškou | **ne** (jen nejvyšší výška jako text v kartě) | – |
| konvexní obálka přeletů („koridor“ z 2026-09-30) | **ne** (zrušeno 2026-10-01) | – |

**Důsledek pro scénář:**
- „Koridor“ v `max-6.4` je dnes **letová plocha**: fialový polygon spojující vlek s polem. Nastaví se N2 a ukáže se v plánovači. `max-6.2` a `6.4` nesmí tvrdit „bílé čárkované přelety vedou po koridoru“ ani „červené body překážek“ (je to v `docs/DRON.md` ř. 576–584, ale **kód to nekreslí**, dokumentace je zastaralá).
- Viditelný účinek plochy v planneru je jen posun trasy: změní se údaje „přelet (výška a délka)“ ve kartě, případně zmizí oranžový pruh „Výška přeletu 20 m (kvůli překážkám)“ nebo vznikne červená hláška „Vlek stojí mimo letovou plochu“ (tu nechtít).
- Pro opravdu čitelný přelet je jediná cesta **svislý letecký záběr se světovými čarami** (`worldLines on`, N2): bílé přelety a fialová plocha. Porušuje to Z5 („debug čáry“); rozhodnutí je na dramaturgovi/Pavlovi. Doporučuji nechat plánovač a změnit text záběru.
- Plocha je **po poli**: nutno nejdřív `selectField` (pole 2) a plochu navrhnout pro to pole. Samoprotínající se polygon se nekontroluje (pravidlo sudý–lichý).

## 5. Rybník (O1, O2, O4): požadavky a postup

`whPond` (`SprayDroneDebug.waterHoseSim`) přepne vstup pumpy na rybník a hledá vodu v **čtverci ±8 m** (celočíselná mřížka) kolem vstupní spojky pumpy; „voda“ = raycast `CollisionFlag.WATER` s hloubkou ≥ `pump.minDepth` (XML 0,15 m) nad terénem. Sací hadice 10 m, výstupní 12 m, průtok 16 l/s. `whOut` připojí výstup na nejbližší **volný** vodní ventil jiného vozidla do 12 m.

**Požadavky na místo (pro Maxe, 5m a celý Middle):**

1. Voda ≥ 0,15 m hluboká do 8 m od místa pumpy (lépe 4–6 m, ať má hadice průvěs); hladina aspoň zhruba 15 × 15 m, ať to vypadá jako rybník.
2. Vodní ventil Maxu (levý bok, `waterHosePort3000`/`B`) do 12 m od výstupu pumpy, doporučeno 3 m (jako `stationAt`); **ventil musí směřovat k vodě**, pumpa mezi vlekem a vodou. Max tedy stojí podél břehu levým bokem k vodě.
3. Rovná, pevná, **otevřená** plocha pro soupravu (MT655 + Max ≈ 15 m × 3,5 m) plus okolí pro oblet kamerou: cca 30 × 25 m bez stromů (TREE maska), `groundCheck`: kola −0,18…+0,30 m od terénu, náklon ≤ 6°.
4. Nad plošinami dronů a v ose stoupání volno aspoň 25 m vertikálně (jinak pojistka dronu, `STATUS_OBSTACLE`) a nad kamerami žádná koruna (kamera koruny nezná, `check` jen varuje).
5. Pro Middle: totéž bez pumpy; místo do ~25 m od hladiny, aspoň jedno vlastnitelné pole do dosahu rádia (450 m) nebo relé.
6. Slunce 17:30–17:50 nízko na západě: břeh ve směru, kde hlavní záběry mají slunce za kamerou, a les nevrhá stín na vlek (O13, Z8).
7. Přístup netřeba (vozidla se přenášejí `placeSet`), ale `placeSet` přenáší hráče do 10 m od cíle a kola potřebují fyziku.

**Postup ověření O2 (na místě):** `spawnMod waterPump diesel=10` → `moveVehicle` → `setTank main EMPTY` → `dbg whDrop` → `dbg whPond` → `dbg whOut` → `dbg pumpOn` → po 5–8 s `dbg whStatus` (log „SDT děj: tok začal“) a `dbgCmd status`. `whPond` a `whOut` se provedou na **každém** vozidle s pumpou (násypka je také pumpa), proto v té scéně žádná násypka. Neověřeno ve hře s rybníkem (v `davka_B` jen cisterna).

**Průzkum místa bez nového příkazu:** `eval` souborem v `tmp/`, který nastaví `FS25_SprayDroneTrailer.SprayDroneDebug.view = {radius, step, apartMin, count, cx, cz}` a zavolá `...SprayDroneDebug.shoreScan()` (rovný břeh, odstup, 25 nejbližších; hlásí jen rovinu ±4 m, ne volný prostor) a `waterMap` (ASCII mapa vody do logu). Rovinu 30 × 25 m a stromy je potřeba dopočítat vlastním skriptem (výška terénu po 2 m, raycast `CollisionFlag.TREE`). Záložní místo z `davka_A/B`: řeka (440,−230), sklon 4,5°; `whPond` funguje na jakékoli vodě.

**O4 (zmizení pumpy):** ověřeno čtením. Hadice pumpy patří pumpě (`pump.hoses`), `isPortOccupied` ignoruje smazaná vozidla, po `removeVehicle` tedy nic nevisí a ventil je volný. Střih na shodu: jeden take, uzamčená kamera (`camSet`), `setTime lock=true`, stejné světlo. Hladina, tráva a stromy se hýbou i v „stejném rámu“; střih to unese.

## 6. Stejná akce pro čtyři kamery (AI jízda, drony nejsou deterministické)

Pozor: jde o **čtyři po sobě jdoucí take** téže akce, nikoli čtyři kamery naráz. Každý take má shodný „reset“, shodný start a jinou kameru; vzájemnou posunutost se měří a zaznamená.

**Protokol jednoho take (akce + kamera):**
1. **Reset (R, I, T, S):** `isolate`, `setWeather`, `setTime lock=true`, `setField` (plodina a růstový stav) + **`resetField`**, `play command=windOff`, `fold fold wait` → `placeSet` (teleport na startovní místo, vždy stejné x, z, yaw; `placeSet` si sám zopakuje přesun až 12× při špatných kolech) → `fold unfold wait` → pauza 6 s → `groundCheck`. `droneSet battery= tank=`, `setTank` (hlavní, koncentrát), `generator batteries=1 fuel=10`, `dbg whDrop`, `toolboxSet` (N5).
2. **Předpozice kamery** `camSet` ještě před záznamem, `mark ready` (N7), `record start lead=0.5`.
3. **Událost místo hodin:** kamera, která má navazovat na událost (vzlet, přistání, spuštění pumpy), se spouští přes `{"after": "<mark>"}` v `mk_take.py` až za `waitDrone`/`waitDrive`, nikoli po pevném `sleep`. Pevné `sleep` jen tam, kde akce nemá čekací příkaz (sekvence animací).
4. **Jízda (nedeterministická):** startovat vždy ze stejného místa s rozjezdem ≥ 60 m před prvním viditelným úsekem (ustálená rychlost, `driveTo kmh=` pevné, `tel=true` loguje polohu, rychlost a yaw každý snímek). Počítat s odchylkou času průjezdu referenčním bodem do ±0,7 s a boční do ±0,3 m; měřit z `TEL` logu (`tel_analyze.py` už existuje) a zapsat `t_ref` do `clips.json`.
5. **Drony (deterministické v prostoru, ne ve startu):** stejná dráha díky stejnému poli, pokrytí (`resetField`), baterii, nádrži, bezvětří a pevnému času; start s jitterem 0,05–0,3 s od příkazu. Zlepšení: `seq` (N7) a značka `mark takeoff` ve chvíli `waitDrone airborne`. Dráhy ověřit `trace on` (logy `DRN` po 250 ms).
6. **Kontrola take proti prvnímu (referenčnímu):** shoda z logů: čas klíčové události (`CINEMA t=`, `MARK`, `TEL`, `DRN`) a polohy dronů v časech 5, 10, 15 s od události. **Tolerance:** událost ±0,5 s, poloha dronu ±3 m, poloha soupravy ±0,3 m. Mimo toleranci: take znovu.
7. **Tolerance pro střih:** střih mezi kamerami dělat v době, kdy v ±0,5 s není diskrétní událost (zapnutí pumpy, odpojení koncovky, dopad kanystru); u diskrétních událostí střihat „na událost“ podle `t_ref` z `clips.json` (každý klip dostane `t_event`, a střih zarovná podle něj, ne podle začátku souboru). Rámce ±0,5 s se mezi kamerami nepoznají u plynulého pohybu (jízda, let, oblet); u diskrétních událostí by byly vidět.
8. Do `clips.json` doplnit `t_event`, `t_ref` a `sync_dev` (odchylka vůči referenčnímu take).

**Co jde přesně:** animace (rozložení, sklopení, výměna baterie, servis) jsou řízené `dt`, takže jejich průběh je shodný od okamžiku startu. **Co ne:** okamžik startu (jitter příkazu), jízda z klidu (fyzika), pojistka dronu proti překážce (raycast), vítr.

## 7. Posudek otevřených otázek O1–O25

| O | verdikt technika |
|---|---|
| O1 | **Blokující.** Kap. 5 (požadavky a postup). Do průzkumu je `middle` beaty 3–8 i `max-5m` ve stavu A\*; rozhodnutí o náhradě (řeka) po průzkumu |
| O2 | Příkazy existují (`whPond`, `whOut`, `pumpOn`); postup v kap. 5; neověřeno ve hře s rybníkem |
| O3 | Technicky bez problému: každá scéna je samostatná (`placeSet` + `fold unfold`, ~10–15 s přípravy, mimo záznam). Doporučuji nechat Maxe na dvoře a pro 5m jen jinou akci |
| O4 | Vyřešeno čtením (kap. 5) |
| O5 | Vyřešeno N3 (kap. 3). Souběžný vzlet není možný (plošina), odstup ~3 s zůstane |
| O6 | Planner kreslí jen fialovou plochu, nikoli přelety (kap. 4); příkaz N2 |
| O7 | Čísla polí ověřit `ui plannerInfo`/`dbgCmd fieldInfo` na místě. `selectField own=true` **trvale mění vlastnictví pole** v slotu 13 (poznamenat do úklidu). Pole 83 je u řeky (440,−230), ne nutně u rybníka |
| O8 | Pohled z dronu jde `camPath at="…:drone1" full=1` (kap. 2.2), Alt+9 není potřeba; ověřit osu uzlu a že HUD není vidět (cinema ho skrývá `hideScene`) |
| O9 | Planner kreslí své ikony jen pro vlastní vlek, dron a tyče; ostatní značky pocházejí z vanilla mapy (`davka_U`: „ikony vleků a dronů“). Řešení: parkoviště mimo okno mapy (I) nebo N8 |
| O10 | `nodeVis` před `fold unfold` (vzor `b09`); zda se stožár vysune viditelně, ověřit zkouškou |
| O11 | Netechnické; 12 s animace je neměnná, střih na 10 s |
| O12 | `canisterPour fill=diesel` v kódu je; ověřit uzel `dieselNeckNode` na Maxu. Z9 viz O14 |
| O13 | Světlo 17:30 zkusit při průzkumu místa; čas se nastavuje `setTime lock=true` |
| O14 | Kanystr a big bag jsou kinematické předměty; rámy: kamera nad nebo ≥ 1,5 m od spodku, ne zblízka zespodu (`canisterPour` zvedá 2 s, naklání 2 s, lije 7 s; big bag nahoru `up=3,4 m`) |
| O15 | `droneSet battery=0.2 tank=0` jako `c55`; potvrzeno v `davka_B` (5 s výměna) |
| O16, O17 | Netechnické přijetí: hladina ani prach vidět nejsou. U 5m.6 spoléhat na big bag a log (`dbg`/`millDbg`, `bagStatus`) |
| O18 | Netechnické |
| O19 | `reverseAttach` existuje (vzor `c61`), A |
| O20 | Displej svítí 10 min po vzniku vleku, jinak až při otevření plánovače; N10. Obsah je statický emisní panel, ne mapa |
| O21 | Obě pořadí jdou: hadice (`whConnect`) i big bag (`bagLift`) na sobě nezávisí; mlýnek musí být do 12 m od spojky |
| O22 | N9; BET určí průzkum; štítky kanystrů, pumpy, násypky a pytle čitelné z fov 25–35 ověřit; **drony S/M/L jako předměty jsou nejrizikovější (nejisté klonování)**; záložně `prod-6` na plošině Maxu s výjimkou ze Z1 |
| O23 | Netechnické; záznamový čas se v odhadu počítá po akcích, ne po záběrech (kap. 6) |
| O24 | Odpojení tahače jde (`detachFrom`, `placeSet`), zjednodušení scénáře je v pořádku |
| O25 | `groundCheck maxTilt 9` na SIL; u 10m soupravy na svahu 6,4° hlídat, že přední kola nejsou ve vzduchu (kola −0,18…+0,30 m) |

## 8. Další nálezy, které v O-seznamu nejsou

- **F1 (vysoká):** planner nekreslí přelety ani překážky (kap. 4); text `max-6.2`, `max-6.4`, případně `mini-6.2` a `middle-6.2` upravit.
- **F2 (vysoká):** `bagLift` pracuje s násypkou (`limeHopper`, jemné vápno `SDT_FINE_LIME`), mlýnek má vstup na **hrubé** vápno (vanilla `LIME`, `exactFillRootNode`) a výstup hadicí nebo do big bagu s jemným vápnem. Scénář píše „big bag nad násypku mlýnku“; to dnes dělá jen N6 nebo se musí zaměnit za násypku. Dramaturg ať rozhodne, zda do 5m patří násypka (`c62` ověřeno).
- **F3 (střední):** `dbg whPond/whOut/whConnect<N>/whValve/whDrop` se provedou na **všech** vozidlech s hadicí (včetně násypky a ostatních vleků). V scénách s hadicemi musí být izolace úplná.
- **F4 (střední):** `toolboxOpen` je **přepínač** (všech částí), stav po minulém take rozhodne, zda se bedna otevře nebo zavře; N5.
- **F5 (střední):** natáčení trvale mění slot 13 (vlastnictví polí `selectField own`, letové plochy v `vehicles.xml`, zaparkované soupravy, `setField`). Do plánu natáčení přidat úklid, nikdy neukládat hru během natáčení.
- **F6 (nízká):** `ui shopOpen` volá `camStop`, `plannerOpen` ne; po záběrech v planneru kameru vypnout výslovně.
- **F7 (nízká):** zakázaná světová čára (Z5) je ve výchozím stavu vypnutá (`showWorldLines = false`), takže ji dev mód nesmí zapnout mimo N2 `worldLines`.
- **F8 (nízká):** `placeSet` při zapnuté izolaci přenáší hráče (`playerNear`), proto parkoviště a scény mají pořadí „nejdřív parkování, potom cílová souprava“ (hráč zůstane u cíle).
