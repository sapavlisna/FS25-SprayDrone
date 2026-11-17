# Dron: jak má fungovat (zadání pro implementaci letu)

Popisuje chování postřikového dronu u malého servisního vleku `FS25_SprayDroneTrailer`
(`mod/FS25_SprayDroneTrailer`). Co je hotové a co se teprve staví, je v sekci **Stav**.

## Scénář hráče

1. Hráč přiveze vlek autem k poli a zastaví. Vlek zůstane zapřažený, nebo ho odpojí.
2. Rozloží vlek (klávesa skládání, výchozí `X`). Middle a Max: rozložit jde jen vlek, který nestojí příliš nakloněný (max. 5°, náklon se ukazuje v nápovědě), vyklopí se
   žebřík na pravém boku a pak se na plošině rozloží dron (ramena, pak listy). Mini: sklopí se boční plechy, rozloží se panely bedny
   do plošiny na nožičkách; dron zůstává v bedně a na plošinu ho přendá hráč (R, okamžitě, viz „Malý vlek“). Při složení vleku se dron složí jako
   první (listy, pak ramena), potom žebřík; Mini se s dronem na plošině složit nedá („Nejdřív přendej dron do bedny“).
3. Nastoupí do vleku (`E` u vleku, nebo `Tab`). Do složeného vleku nastoupit nejde.
   Je to stanoviště pilota: kamera kolem vleku, žádné řízení jízdy.
4. Kolem vleku je ve světě vidět **kruh dosahu** dronu (počítá se z energie baterie, strop `maxRange` podle varianty dronu: S 600 m, M 900 m, L 1200 m).
5. Hráč otevře **plánovač letu** (`Alt+7`): celoobrazovková herní mapa vycentrovaná na vlek, s označeným
   vlekem, kruhem dosahu a obrysy polí v okolí. Klikne na pole: **vlastní pole** farmy, nebo pole
   **přijaté zakázky** na hnojení či herbicid. Pole mimo dosah, cizí pole a zakázku, která potřebuje
   jiný přípravek, než je ve vleku, vybrat nejde; plánovač u kurzoru napíše proč.
6. Mod **spočítá trasu** a vykreslí ji do mapy: rovnoběžné řádky přes polygon pole (boustrophedon)
   s roztečí rovnou záběru postřiku (`workWidth`, výchozí 9 m, podle DJI T50). Řádky se ořežou dosahem
   a rozdělí na **dávky** (barva čáry = dávka): jedna dávka je tolik práce, kolik dron zvládne s jednou
   nádrží (40 l) a baterií, která v dronu právě je (sekce Baterie), včetně cesty tam a zpět. Panel ukáže počet dávek, plochu, potřebné
   litry proti obsahu vleku a dronu a přípravek.
7. Hráč trasu **odsouhlasí tlačítkem Spustit let**. Dron vzlétne z plošiny vleku, doletí na začátek
   dávky, letí řádky ve výšce `sprayHeight` (3 m nad terénem) a postřikuje. Když dojde nádrž, baterie
   nebo dávka, vrátí se. Plánovač může zůstat otevřený: poloha dronu a zbývající trasa se v něm
   průběžně ukazují.
8. Na vleku přistane, hadicí se postupně doplní nádrž z nádrže vleku (hnojivo nebo herbicid, podle toho, co ve
   vleku je) a když je baterie pod 30 %, vloží ji do nabíječky a vezme si první plně nabitou; nabíječka nabíjí
   všechny baterie najednou z elektrocentrály na naftu. Když žádná není nabitá, dron čeká. Pak letí na další dávku.
   Opakuje se, dokud není pole hotové.
9. **Návrat domů** (tlačítko v plánovači nebo `Alt+0`) přeruší let kdykoli: dron nechá rozpracovaný
   řádek, vrátí se na vlek a přistane. Po dalším spuštění pokračuje tam, kde je pole ještě neošetřené.
10. Při vystoupení z vleku let pokračuje. Při složení nebo odjetí vleku se let nejdřív
    ukončí přes return home. Složit vlek jde až po přistání dronu.

## Jak postřik působí na pole

Dron používá stejné mechaniky jako pozemní postřikovač, nic vlastního:

- **Tekuté hnojivo** (`LIQUIDFERTILIZER`) zvyšuje úroveň hnojení (`sprayLevel`) jako vanilla
  postřikovač s tekutým hnojivem.
- **Herbicid** (`HERBICIDE`) ničí plevel (`weed`) jako vanilla postřikovač s herbicidem.
- Plocha se ošetřuje po pruzích pod dronem: šířka `workWidth`, délka podle uletěné dráhy.
  Hra si stav pole sama ukládá, takže persistence ošetřené plochy je zadarmo.
- Spotřeba jde po litrech na hektar podle fill type (`g_sprayTypeManager`), stejně jako u vanilla.
- **Zakázky**: pole zakázky jde vybrat, když na něm běží zakázka farmy vlastníka vleku a dovoluje postřik
  (`mission:getIsWorkAllowed(farmId, x, z, WorkAreaType.SPRAYER)`, tedy hnojení a herbicid) a přípravek ve
  vleku sedí k typu zakázky (hnojení = hnojivo, `herbicideMission` = herbicid). Každý kousek postřiku
  projde stejnou kontrolou jako pracovní plocha vanilla stroje (`WorkArea:getIsAccessibleAtWorldPosition`):
  `accessHandler:canFarmAccessLand` nebo `g_missionManager:getIsMissionWorkAllowed`. Zakázka si postup
  počítá sama z density mapy (`AbstractFieldMission:getFieldCompletion`), dron do ní nic nezapisuje.
- Statistiky `sprayedHectares` a `sprayUsage` jdou jako u vanilla `Sprayer` farmě, které patří ošetřený
  pozemek (`getLastTouchedFarmlandFarmId`); u zakázkového pole je to vlastník pozemku (NPC, farm 0), ne hráč.

## Persistence a multiplayer

- **Neukládá se pozice dronu ani rozpracovaná trasa** (viz `PLAN.md`, sekce Persistence). Uloží se
  jen: vybrané pole (farmland/field id), jestli je mise aktivní, stav nádrže a baterie dronu, náboj náhradních baterií,
  zapnutí centrály (nafta je vanilla `fillUnit`) a letové plochy
  polí (sekce Letová plocha).
  Po načtení je dron na vleku a trasa se přepočítá z aktuálního stavu pole, takže rozletí jen
  zbytek.
- Let se počítá a simuluje **na serveru**. Klienti dostávají polohu dronu po síti (dirty flag, stream),
  příkazy (výběr pole, start, return home) a letová plocha jdou jako eventy od klienta na server.

## Model a uzly v i3d

V `sprayDroneTrailerMiddle.i3d` jsou **tři drony** (varianty S, M, L, sekce Varianty dronu), všechny na plošině
uprostřed heliportu (kořeny v (0; 2,505; 0)), nosem po směru jízdy, se složenými rameny i listy. Viditelný je jen
ten z konfigurace. Uzly mají prefix varianty `Drone_S_`, `Drone_A_` (M) nebo `Drone_L_` a stejné přípony:

| i3dMapping | co to je |
|---|---|
| `<prefix>Root` | kořen dronu. Počátek je uprostřed pod lyžinami, stojí na horní plošině. Za letu nese polohu a yaw. |
| `<prefix>Tilt` | náklon za letu (pitch/roll), 0,53 / 0,55 / 0,65 m nad lyžinami (S / M / L); pod ním všechny díly |
| `<prefix>ArmPivot_1..4` | kloub ramene (otáčí se kolem svislé osy) |
| `<prefix>Rotor_<i>Top/Bottom` | vrtule (M, L souosé páry, S jen `Top`), točí se kolem svislé osy; pod ní dva listy |
| `<prefix>Blade_<i><Top/Bottom><0/1>` | list vrtule, počátek ve středu náboje (skládá se kolem něj) |
| `<prefix>FillPort`, `<prefix>BatterySlot` | plnicí hrdlo (+Z do hrdla) a lůžko baterie na trupu |
| `padClampL`, `padClampR` + `padClampHingeL`, `padClampHingeR` | úchyty lyžin: součást plošiny (ne dronu, stejné pro S, M, L), jedna překlápěcí příčka na stranu; u druhé plošiny Maxu s příponou `2` (`padClampL2` …). Mini je nemá |
| `<prefix>SprayNozzle_k` | výstup trysky (S a L 2, M 4); poloha je v šabloně i jako `effects.nozzle#x/#z` |
| `battery1..5` + `battery<i>S/M/L` | kořen baterie a tři modely podle varianty (skript ukáže ten varianty) |
| `batterySlotDeck1..5` | šachty nabíječky `batteryCharger` v truhle na horní palubě (stálé místo baterií) |
| `fillHoseCoil`, `fillHoseStart`, `fillHoseLay1..8`, `fillHoseSeg1..96`, `fillHoseNozzle`, `fillHoseParkPos` | plnicí hadice (sekce Plnění) |
| `sprayDroneTrailerMiddle_main_component1` | fyzikální komponenta vleku (enterReferenceNode) |
| `outdoorCamera`, `outdoorCameraTarget` | kamera pilota, otočná kolem plošiny |
| `exitPoint` | kam hráč vystoupí |
| `<prefix>Led_1..4` | kulatá čočka poziční LED v pouzdru na straně ramene u motoru (dítě `ArmPivot`, skládá se s ramenem), materiál `SDT_NavLed` |
| `<prefix>LedLight_1..4` | bodové světlo před čočkou (dítě čočky, dosah 3 m, bez stínů) |
| `generatorExhaust` | výfuk elektrocentrály: kouř a zvuk |
| `ladderHinge` > `ladderTrigger`, `colLadder` | sklopný žebřík (kloub = čep nahoře, sklopí se o 90° dolů z vodorovné polohy podél boku) se spouštěčem lezení a kolizí, `ladderGrab` = madla (sekce Žebřík); Middle a Max |
| `Toolbox_Door` | rolovací vrata skříně na kanystry (pivot nahoře uprostřed otvoru, jede nahoru o `doorTravel`); Middle a Max |
| `padSideL/R`, `padHingeZ/H/P`, `padLeg1..6` | boční plechy a panely skládací bedny s dronem, nožičky plošiny; jen Mini (sekce Malý vlek) |

Natočení kloubů složeno/rozloženo nejsou v i3d, ale v XML (`<foldPart>` pod `<sprayDrone>`, viz níž); počítá je
`blender/export_middle_mod.py` z geometrie (`drone_fold_parts` v `build_trailer_middle.py`: motor ramene dosedne do rohu
rozteče motorů S 1,315 × 1,405, M 1,425 × 1,71, L 1,646 × 1,65 m = rozměr rozloženého dronu s vrtulemi podle DJI (T25 2585 × 2675, T50 2800 × 3085, T100 3220 × 3224 mm) minus průměr vrtule;
horní listy se roztáhnou napříč ramene, spodní podél). Náhled v Blenderu:
`set_drone_unfold(0..1)`.

**Složený tvar** (2026-10-28, Pavel: „ve složeném stavu má Max ramena přes trup“; předloha: složený DJI Agras T50 shora v `reference/drone/t50/771253fa7f43….jpg`,
rozměry složeného T25 1050 × 690, T50 1115 × 750, T100 1105 × 1265 mm): ramena leží **podél boků trupu**, přední dozadu a zadní dopředu, motory na obou koncích
(dřív všechna dozadu a ven, M 2,3 × 1,5 m, teď ~1,2 × 0,9 m). Kloub sedí na boku trupu (`body_width / 2`, pozor: lokální `hy` v `build_drone` se po stavbě čerpadla přepíše),
přední kloub u trupu, zadní o `lane_gap` (šířka listů + náboj kloubu) dál ve vnějším pruhu na výložníku `Outrigger_i`, který zůstává na trupu, aby se oba páry
nekřížily. Listy leží podél ramene dovnitř (`pair` u všech variant, směr podle skutečného ramene root → špička). Cíl skládání je v `build_drone` (`target_az` π / 0),
rozložení počítá export z geometrie jako dřív (motor do rohu rozteče, ověřeno odchylkou ≤ 0,0001 m). Při skládání se přední a zadní rameno stejné strany na okamžik
protnou (skutečné mají jinou výšku kloubů).

Vzhled dronů (2026-09-29, Pavel: „je to škaredý“; `blender/build_drone.py`, reference z ag.dji.com v
`reference/drone/`): S = T25, M = T50, L = T100. Šedý fasetovaný trup s válcovým radarem vpředu a čelním modulem s
dvojicemi světel, zadní část hřbetu (za radarem) bílá jako horní stěna nádrže, pod trupem velká bílá fasetovaná nádrž,
štíhlá karbonová ramena s černým skládacím kloubem a žlutým štítkem, souosé bílé gondoly (S jedna), ESC s žebry na
ramenech S a L, listy M bílé, S a L černé s oranžovou špičkou, A-nohy s podélnými lyžinami. Meshe se skládají po
skupinách (`Mesh` v `build_drone.py`), jména uzlů pro skript se nezměnila. Plnicí hrdlo je vpravo od baterie
(`DRONE_FILL_PORT`), radar vpředu. Baterie (`sdt_parts.battery`): černý zkosený blok, konektorová deska s pěti
kontakty, oranžový štítek s diodami a madlo na čele, pojistné lišty a větrací štěrbiny na bocích.
Původní podoba je zálohovaná v `blender/archiv/2026-09-29_drony_pred_DJI/`.

Při vzletu skript `<prefix>Root` přepojí pod kořen scény (`link(getRootNode(), node)` se zachovanou
světovou polohou) a řídí jeho `setWorldTranslation/Rotation`. Po přistání ho vrátí pod vlek do
původní lokální polohy. Dron nemá fyziku (kinematický let), překážky hlídají raycasty (sekce **Překážky**).

## Parametry (výchozí, v XML vozidla `vehicle.sprayDrone`)

Sekce `<sprayDrone .../>` je v `sprayDroneTrailerMiddle.xml` i v šabloně `blender/templates/sprayDroneTrailerMiddle.xml.in`
(statický text). `vehicle.xsd` ji nezná, takže `tools/validate_mod.py` na ní hlásí chybu schématu — to je v pořádku.

| parametr | hodnota | poznámka |
|---|---|---|
| `fillUnitIndex` | 1 | nádrž vleku, ze které se dron doplňuje |
| `maxRange` | 1500 m (výchozí) | strop dosahu počítaného z baterie (sekce Dosah); **v bloku `<drone>` slotu 1 je přepsaný: S 600 m, M 900 m, L 1200 m** (malý dron = menší dolet, rozhodnutí Pavla 2026-10-05; kód čte `value("maxRange")` nejdřív z bloku varianty). Pevný `range` v XML není, kdyby byl, je to další strop |
| `workWidth`, `tankCapacity`, `batteryMinutes`, `droneMass`, `batteryMass`, `batteryKwh`, `droneRadius`, `rotorPitch` | podle varianty | v bloku `<drone>` varianty (sekce Varianty dronu); `droneMass` je bez baterie, let počítá s `droneMass + batteryMass` |
| `sideClearance` | 4 m | výchozí boční odstup dráhy od překážek (nastavení v plánovači 1–15 m) |
| `turnAcceleration` | 2,5 m/s² | boční zrychlení v oblouku, rychlost na oblouku √(a · r) |
| `batteryHoverFactor` | 1,15 | násobek odběru při vznášení a otáčení na místě (pod 2 m/s vodorovně) |
| `batteryClimbFactor` | 1,4 | násobek odběru při stoupání (nad 0,5 m/s) |
| `batteryDescentFactor` | 0,8 | násobek odběru při klesání |
| `batterySwapBelow` | 0,3 | na vleku se baterie vymění, když je pod 30 % (nebo když na další dávku nestačí) |
| `trailerFoldEnd` | 0,667 | dron se skládá v čase 0..0,667 skládání vleku (0 = rozloženo), tj. prvních 2 s ze 3; rozkládá se stejně plynule (skript drží rychlost, i když vanilla animace při přehrávání pozpátku skočí na konec) |
| `cruiseSpeed` | 10 m/s | přelet a přejezdy mezi řádky |
| `sprayingSpeed` | 7 m/s | rychlost při postřiku |
| `climbSpeed` | 3 m/s | klesání (u země ještě zpomaluje, viz Let) |
| `ascentSpeed` | 5 m/s | stoupání |
| `acceleration` | 2,5 m/s² | rozjezd i brzdění, vodorovně i svisle |
| `yawSpeed` | 90 °/s | nejvyšší rychlost otáčení |
| `sprayHeight` | 3 m | výška nad terénem při postřiku |
| `transitHeight` | 12 m | nejnižší výška přeletu vlek ↔ pole nad terénem (výchozí; nastavení v plánovači 5–40 m) |
| `obstacleClearance` | 5 m | odstup přeletu nad nejvyšší překážkou úseku (výchozí; nastavení 2–20 m) |
| `maxTransitHeight` | 60 m | výš dron nesmí; překážka nad limit = dávku nejde letět |
| `corridorHeight` | 8 m | nejnižší výška přeletu letovou plochou (místo `transitHeight`, když je plocha nakreslená) |
| `usageScale` | 0,2 | násobek spotřeby oproti vanilla (jako `usageScale` u `Sprayer`); 0,2 = ~58 l/ha místo 292 l/ha (všechny tři vleky, rozhodnutí Pavla 2026-10-05) |
| `litersPerSecond` | 1 l/s (výchozí) | čerpadlo, kterým se dron na plošině plní z nádrže vleku; **v bloku `<drone>` slotu 1 podle varianty: S 1 l/s (60 l/min), M 1,5 l/s (90 l/min), L 2,5 l/s (150 l/min)**, tedy každý dron se plní ~20–30 s (původně 0,4 l/s) |
| `securedFoldTime` | 0,8 | od kterého času skládání vleku jsou úchyty lyžin zavřené („Dron zajištěn") |
| `power#dieselFillUnitIndex` | 2 | nádrž elektrocentrály (nafta, 30 l) |
| `mixer#concentrateFillUnitIndex` | 3 | nádrž koncentrátu: 5 % hlavní nádrže (Middle 40 / 50 / 75 / 150 / 250 l pro 800 / 1000 / 1500 / 3000 / 5000 l, Max 300 / 500 l, Mini 50 l; kapacita je v každé `fillUnitConfiguration`), viz „Koncentrát a mixér“ |
| `mixer.ratio#fillType`, `#concentrate` | hnojivo 0,05, herbicid 0,05 | podíl koncentrátu v hotovém přípravku (zbytek voda) |
| `power#batteries` | 3 | počet baterií bez konfigurace; s konfigurací `sprayDroneBattery` 0–5 |
| `chargeMinutes`, `dieselPerHour` | podle varianty | nabití z 30 na 95 % (S, M 10 min, L 8,5 min) a nafta **na každou nabíjenou baterii** (S 1,14, M 2,2, L 3,52 l/h) |
| `transfer#drainRate`, `#palletRate`, `#palletDistance` | 1 l/s, 20 l/s, 6 m | vypouštění dronu do vleku, přečerpání vleku do IBC (IBC 1000 l za ~50 s), dosah IBC |
| `fillTriggerVehicle#litersPerSecond` | Middle, Mini 200 l/s, Max 300 l/s | z nádrže vleku se dočerpává pozemní postřikovač zajetý vedle vleku |
| `power#slots` | Middle 5 (výchozí), Mini 3, Max 8 | počet šachet nabíječky (u Mini odpovídá modelu a konfiguraci baterií 0–3) |
| `power#readyLevel` | 0,95 | od kolika procent jde náhradní baterie do dronu |
| `power#swapTime` | 5 s | výměna baterie (souběžně s plněním) |
| `navLights#intensity` | 4 | svit LED ramen (`lightIds0` materiálu) |
| `navLights#lightScale` | 0,3 | násobek barvy bodových světel pod LED (plná barva z i3d celý dron přesvěcovala) |
| `navLights#blinkPeriod`, `#blinkOn` | 1 s, 0,5 s | blikání zadních LED (1 Hz, střída 50 %) |

Pod `<sprayDrone>` jsou bloky `<drone name prefix …parametry…>` variant S, M, L. V každém jsou uzly dronu
(generuje je export z Blenderu do zástupců `{{DRONE_PARTS_S|M|L}}`): `<tilt node>`, `<foldPart node foldedRot
unfoldedRot startTime endTime>` (klouby ramen 0–0,6 času rozložení, listy 0,5–1), `<rotor node direction>`,
`<navLight>`, a ručně psané `<sounds><rotor .../></sounds>` (sekce Zvuk) a `<effects>` (sekce Efekt postřiku).
Úchyty všech tří variant dává export do animace `foldLadder` (`{{CLAMP_PARTS}}`). Konstanty vizuálu jsou ve skriptu:
roztočení 2 s, doběh 4 s, vrtule 35 rad/s.

### Varianty dronu a konfigurace

Vlek se kupuje (a v dílně „Přizpůsobit“ mění) přes dvě konfigurace z modu (`addConfigurationType` v
`initSpecialization`, vanilla obchod i dílna je obslouží samy):

- **Dron** (`sprayDrone`, saveId `S` / `M` / `L`, vždy povinný — žádná varianta „bez dronu“, zrušeno Pavel 2026-10-07):
  Middle: Malý 7 000 €, **Střední 12 000 € (výchozí)**, Velký 22 000 €; Max nese dva drony, takže ceny jsou dvojnásobné
  (Malý 14 000 €, **Střední 24 000 €**, Velký 44 000 €); Mini jen Malý 7 000 € (výchozí). `objectChange` ukáže kořen
  a úchyty vybraného dronu, obchod ukáže záběr varianty.
- **Baterie dronu** (`sprayDroneBattery`, saveId = počet 0–5): 1 500 € za kus, výchozí 3.
- Vlek sám stojí 6 500 €; s M a 3 bateriemi 23 000 €.

| | S (DJI T25) | M (T50) | L (T100) |
|---|---|---|---|
| nádrž / záběr | 20 l / 6 m | 40 l / 9 m | 75 l / 11 m |
| dron bez baterie + baterie | 25,4 + 6,6 kg | 39,9 + 12,1 kg | 60,3 + 14,7 kg |
| baterie | DB800 0,81 kWh | DB1560 1,567 kWh | DB2160 2,13 kWh |
| výdrž s plnou nádrží (`batteryMinutes`) | 9 min | 8 min | 6 min |
| strop dosahu (`maxRange`) | 600 m | 900 m | 1200 m |
| čerpadlo plnění dronu (`litersPerSecond`) | 1 l/s | 1,5 l/s | 2,5 l/s |
| nabití 30 → 95 % / nafta na baterii | 10 min / 1,14 l/h | 10 min / 2,2 l/h | 8,5 min / 3,52 l/h |
| `droneRadius` / výška zvuku `rotorPitch` | 1,35 m / 1,25 | 1,6 m / 1 | 1,65 m / 0,8 |
| trysky (kužely postřiku) | 2 vzadu, x ±0,684, z −0,657 | 4 pod motory | 2 na rameni postřiku, x ±0,917, z −0,823 |

Výdrž S a L je odvozená z výkonu vznášení ~ m^1,5 / √(plocha vrtulí), kalibrovaného na T50 (`out/plan09/L4.md`).
L má 75 l místo 100 l, aby výdrž nespadla pod 5 min. Při změně varianty v dílně se baterie přenesou jako **podíl
nabití** (`battery(i)#level`), přebývající se zahodí, nové jsou plné; typ baterie jde vždy s dronem. Náplň dronu se
ořízne na novou nádrž (bez dronu zmizí). Vanilla dílna účtuje cenu nově vybraných voleb (ne rozdíl) a vlek po změně
znovu vytvoří odpojený.

**0 baterií**: start (`Alt+8`, Spustit let) odmítne s hláškou „Dron nemá baterii, nemůže vzlétnout“.

### Rozložení dronu s vlekem

Animace skládání vleku `foldLadder` (Middle a Max) trvá 3 s (konvence FS25: čas 0 = rozloženo, 1 = složeno): 0–2 s nic v XML
(skládá se dron), 2–2,6 s sklopení žebříku (`ladderHinge`), 2–2,4 s úchyty lyžin, víko truhly nabíječky 1,8–3 s. Dron řídí skript z
`getFoldAnimTime()` (čas `t` = sekundy / 3, rozkládání jde od 1 k 0):

| `t` (s) | děj při rozkládání |
|---|---|
| 1 → 0,6 (3 → 1,8) | víko truhly nabíječky se otevírá (souběžně s ostatním) |
| 0,867 → 0,667 (2,6 → 2,0) | žebřík se sklápí do rozložené polohy, úchyty lyžin se otevírají (0,8 = `securedFoldTime`) |
| 0,667 → 0 (2 → 0) | dron se rozkládá (`sprayDrone#trailerFoldEnd`): ramena 0–0,6, listy 0,5–1 jeho času |

Skládání jde opačně. Rozložení dronu počítá skript z
`getFoldAnimTime()`: `1 - čas / trailerFoldEnd`, takže se při rozkládání vleku dron rozloží až po vyklopení žebříku
(ramena, pak listy) a při skládání se složí jako první (listy, pak ramena). Stav se nikam neukládá ani
neposílá: plyne z Foldable, který ukládá čas skládání do savegame (v `onLoad` ho vrací `getFoldAnimTime`) a
synchronizuje ho po síti. Za letu (dron odpojený od vleku) se rozložení nemění.

- Před vzletem se už nic nerozkládá, jen se roztočí vrtule (2 s); po přistání dron zůstane rozložený.
- Složit vlek jde jen s dronem v doku (`PARKED`/`SERVICING`, jinak se vrací domů) **a** se zastavenými vrtulemi
  dotočenými do klidové polohy (jinak hláška „Vrtule dronu ještě dobíhají“), aby složené listy mířily podél ramene.
- Když hráč sedí ve vleku, vanilla Foldable složení nedovolí vůbec („Nejdřív spusť motor!“); skládá se z tahače.

### Baterie

`battery` je v sekundách vodorovného letu s plnou nádrží (kapacita `batteryMinutes` × 60 = 480 s). Za letu ubývá
každý snímek o `s × (hmotnost / plná hmotnost)² × fáze`, kde hmotnost = `droneMass` + litry v nádrži × hustota
přípravku (`FillType.massPerLiter`, tekuté hnojivo ~1 kg/l) a fáze je 1 (vodorovný let), `batteryHoverFactor`,
`batteryClimbFactor` nebo `batteryDescentFactor` podle pohybu od minulého snímku. Kvadrát hmotnosti sedí na DJI T50:
s plnou nádrží (92 kg) 8 min letu, tj. 7 min vznášení; prázdný (52 kg) 25 min letu, tj. 22 min vznášení. Na plošině se
nevybíjí.

- **Plánování** (`SprayDroneRoute.pathCost` / `planBatch`) počítá čas i spotřebu po skutečných waypointech (zaoblení,
  výškový profil, rozjezd a brzdění, stoupání/otáčení/klesání se svými násobky, hmotnost náplně). Rezerva 30 s. Za letu
  se návrat hlídá hrubším přeletem (`coarseTransit`, ostré rohy = opatrněji). Ve hře 0.9: M pole 4 let / odhad
  50,8 / 50,3, 61,5 / 65,5, 46,0 / 47,6 s, baterie 29,8 / 29,3, 40,8 / 43,3, 33,9 / 34,8 s; S pole 4 47,7 / 47,7 s;
  L pole 2 (přelet 250 m) 166,6 / 172,2 s, baterie 95,3 / 98,4 s. Odhad sedí do −1 až +6 %.
- **Baterie a sloty**: baterií je 0–5 (konfigurace), vlek má 5 slotů: šachty nabíječky `batterySlotDeck` v truhle na
  horní palubě (držák u centrály zrušen, baterie jsou pořád v nabíječce). Po rozložení si dron vezme nejnabitější
  ≥ `readyLevel` (95 %). Při servisu (`power#swapTime` 5 s, souběžně s plněním) se mění jen pod `batterySwapBelow` (30 %)
  nebo když s ní další dávka nejde naplánovat: vybitá jde **hned** do volného slotu (nabíjí se) a do dronu jde první
  plně nabitá (nejnabitější ≥ 95 %). Když žádná není, dron čeká („čeká na nabití baterie – X %"); když dojde nafta,
  mise skončí („v centrále došla nafta"). **Při skládání vleku** poletí baterie z dronu do volného místa nabíječky
  (`BATTERY_STOW_FROM` 6 % animace, 1,4 s) a až potom se zavře víko truhly (`chargerLid` 1,8–3 s animace); při
  rozkládání se po otevření víka (`BATTERY_STOW_UNTIL` 55 %) vrátí do dronu. S jednou baterií se nabíjí ta samá ve slotu.
  Plánovač počítá dávky se stejnými výměnami, ukáže nejvyšší spotřebu dávky v % a počet výměn.
- O výměně se rozhodne hned na začátku servisu (`getWantsSwap`: plán další dávky s nádrží, jaká bude po doplnění),
  takže výměna běží souběžně s plněním; když náhradní ještě není nabitá, vymění se, jakmile dosáhne 95 %.
- S vanilla dávkou (~292 l/ha) vystačí 40 l jen na ~150 m řádku, takže dávku skoro vždy omezí nádrž: dávka na poli
  vedle vleku bere ~9–11 % baterie, s přeletem 300 m ~20 %. Výměna tak přijde zhruba po každé 3.–7. dávce.

### Elektrocentrála a nabíječka

Oranžová skříň v kleci vpředu na palubě (`Gen_0_*`, vzor DJI D12000iE, model `blender/sdt_generator.py`) je elektrocentrála
s nabíječkou: žaluzie, ovládací panel na levém boku (klíč OFF/ON/START, předehřev, voltmetr, hodiny, kontrolky RUN/OIL/TEMP,
jistič, vypínač výstupu, zásuvka `Gen_0_ChargeSocket`), černá nádrž vzadu s hrdlem a ukazatelem hladiny a na střeše tlumič
se zahnutým výfukem, jehož ústí míří dopředu vleku (`generatorExhaust`, osa −Y Blenderu = +Z i3d míří ven, o 12° vzhůru).

- **Nafta**: druhá nádrž vleku (`fillUnit` 2, `diesel`, 30 l jako nádrž D12000iE) s vlastním `exactFillRootNode`
  (`dieselFillRootNode`, kinematický kvádr přes centrálu, skupina `0x40000000` jako plnicí uzel nádrže). Čerpací
  stanice (`gasStation01.xml`, `loadTrigger fillTypes="DIESEL"`) i nádrž na naftu na farmě plní přes `loadTrigger`,
  který hledá právě `exactFillRootNode`; bez něj by vlek nenatankoval. Ve hře ověřeno na stanici u (-798, -250):
  pickup s vlekem v triggeru, akce Natankovat (R), 2 → 30 l, −42 €. Stav je ve vanilla ukazateli naplnění a v plánovači.
- **Nabíječka** (`batteryCharger`, krabice se šachtami v levém předním rohu horní paluby, uvnitř truhly s víkem
  `chargerLid`; s centrálou ji spojuje volně prověšený kabel `chargerCable`, který je vidět jen u rozloženého vleku) nabíjí **všechny nenabité baterie ve slotech najednou**, každou rychlostí 65 %
  kapacity za `chargeMinutes` (30 → 95 % za 10 min u M; bez zpomalení nad 95 %). Baterie v dronu se nenabíjí.
  Ve hře ověřeno: dvě baterie 60 % a 25 % rostly stejně rychle (+1,1 %/10 s), s 5 bateriemi log „nabíjí 4 ks“ → „3 ks“ → „2 ks“.
- **Spotřeba**: `dieselPerHour` **na každou nabíjenou baterii** (M 2,2 l/h; 3 vybité = 3×), jen když se nabíjí
  (centrála bez zátěže se vypne), tj. ~0,37 l na nabití M 30 → 95 %. Hodnota: D12000iE dává 9 kW DC, jedna baterie DB1560
  (30 Ah × 52,22 V = 1,57 kWh) nabitá z 30 na 95 % je ~1,0 kWh za 10 min, tedy ~6 kW do baterie a ~7 kW z centrály
  se ztrátami; dieselová centrála má měrnou spotřebu ~0,3 l/kWh (≈250 g/kWh) → ~2,1–2,3 l/h. (Originál D12000iE je
  benzínový, DJI udává 0,5 l/kWh při 9 kW, tj. ~4,5 l/h benzínu.)
- **Kdy běží**: kdykoli je zapnutá, je nafta a některá náhradní baterie je pod 100 %: nezávisle na misi, i u složeného
  vleku a bez nikoho ve vleku (na farmě, za jízdy). Vypnout / zapnout jde `B` ve vleku (`IMPLEMENT_EXTRA`), z tahače
  s vybraným vlekem, nebo pěšky `B` u výfuku centrály (`SDT_TOGGLE_FOOT`, `SprayDroneLink`) (text akce „Dron: vypnout / zapnout elektrocentrálu"); stav
  `generatorEnabled` jde eventem `SprayDroneCommandEvent.SET_GENERATOR` na server, ukládá se a synchronizuje.
  Vypnutá centrála nenabíjí ani během mise (dron pak čeká na baterii, dokud se nezapne). Během běhu hraje vanilla zvuk motorového čerpadla (`soundTemplates` `riceFieldPump`, 3D u výfuku) a z výfuku
  jde vanilla kouř (`$data/effects/exhaust/exhaust.i3d`, shader `exhaustShader`, parametry `param` a `exhaustColor`).
- **Nabíjecí stanice pro elektromobily**: nepodporuje se. Vanilla stanice (`placeables/brandless/chargingStation`,
  `loadTrigger fillTypes="ELECTRICCHARGE"`) na Riverbend Springs předem postavená není, takže by nešlo nic ověřit.
  Šlo by to přidat třetí `fillUnit` `ELECTRICCHARGE` (bez zobrazení, kapacita sady ~3,1 kWh) s vlastním
  `exactFillRootNode`: stanice by ho naplnila a skript by z něj nabíjel přednostně před naftou.
- **Uložení a síť**: každá baterie `battery(i)#level` (0..1) a `#slot` (0 = v dronu, 1..5 = slot) a zapnutí centrály
  (`#generatorEnabled`) jdou do `vehicles.xml`, nafta do vanilla `fillUnit`, konfigurace do vanilla `configuration`.
  Starší `#charge` (s) se ještě čte. Po síti jdou v `writeState` (nabití a slot každé baterie, běh centrály,
  příznaky plnění / výměny / čekání, režim přečerpávání), za nabíjení nejvýš každých 0,5 s.
- `DEBUG_POWER = true` zapisuje do logu každých 10 s nabití baterií a naftu a změny běhu centrály.

### Plnění dronu na plošině

Po přistání se dron plní čerpadlem `litersPerSecond` (podle varianty S 1 / M 1,5 / L 2,5 l/s; 20 l za 20 s, 40 l za 27 s, 75 l za 30 s) z nádrže vleku, souběžně s
případnou výměnou baterie. Servis trvá nejméně 5 s (`SERVICE_TIME`), jinak dokud se nádrž nenaplní (nebo vlek
nevyprázdní), baterie nevymění a případně nenabije. F1 ukazuje „Dron: plní nádrž (60 l/min)" a v ukazateli naplnění
roste „Nádrž (v dronu)" (stav jde po síti každých 0,5 s). Plánovač počítá s dobou plnění před každou dávkou
(spotřebované litry / čerpadlo), s výměnou a s čekáním na nabití (simulace nabíječky a nafty v
`SprayDroneRoute.splitIntoBatches`, stejné pravidlo výběru baterie jako server), panel ukáže „Servis na vleku X min, z
toho čekání na nabití Y min" (čekání = jen o kolik se servis kvůli nabíjení prodlouží) a „Nafta na nabíjení ~Z l,
v centrále W l" (červeně s upozorněním, když nafta nestačí). Ve hře (pole 4, náhradní baterie 66 %): plánovač 3,8 min
čekání, skutečně vyměněno po ~4,5 min od startu (40 s plnění + nabíjení na 95 %).

**Plnicí hadice** (`SprayDroneService.lua`, `layoutHose`): složený vlek = hadice namotaná na modrém navíječi pod horní
plošinou (`fillHoseCoil`); rozložený = 96 článků (`fillHoseSeg1..96`) leží zkrouceně po pravém zadním kraji horní
desky přes body `fillHoseLay1..8`, koncovka v `fillHoseParkPos`. Při servisu (i při čekání na baterii a vypouštění
`Alt+1`) koncovka za 1,5 s dojede k `<prefix>FillPort` dronu, hadice se z desky zvedne jako prověšená Bézierova
křivka stálé délky (část zůstane ležet), po plnění se vrátí do klidového tvaru; vzlet čeká na návrat koncovky.

**Přečerpávání** (sekce Ovládání, `Alt+1` / `Alt+2`, eventem na server): dron → vlek 1 l/s (dron na plošině, vlek
přijme druh), vlek → IBC 20 l/s (vanilla IBC / paleta s kapalinou do 6 m, i se složeným vlekem a z tahače; opakovaný
stisk zastaví). Když je vlek i dron prázdný, vlek přijme jiný přípravek. Ve hře ověřeno: vlek → IBC 300 → 265 l za
23 s, dron → vlek 40 l.

### Koncentrát a mixér

Vlek má tři fill units (pořadí v XML se nesmí měnit): **1** hlavní nádrž (`water liquidFertilizer herbicide`, 800 /
1000 / 1500 / 3000 / 5000 l podle konfigurace v obchodě), **2** nafta (30 l), **3** koncentrát (vlastní fillTypes `SDT_CONCENTRATE_FERTILIZER` a `SDT_CONCENTRATE_HERBICIDE` z `xml/fillTypes.xml`, 5 % hlavní nádrže: Middle 40 / 50 / 75 / 150 / 250 l, Max 300 / 500 l, Mini 50 l,
`exactFillRootNode` = `concentrateFillRootNode`). Viditelnou skupinu hlavní nádrže (`tankMain800..5000`) přepíná
`objectChange` v `fillUnitConfiguration`. Podíly koncentrátu a číslo nádrže jsou v `<sprayDrone><mixer
concentrateFillUnitIndex="3">` (`<ratio fillType="liquidFertilizer" concentrate="0.05"/>`, herbicid taky 0,05; bez bloku platí
tyhle výchozí hodnoty). Podíl 0,05 od 2026-10-01 (Pavel: 20 l kanystr má vystačit aspoň na nejmenší 300l nádrž;
dřív hnojivo 0,25 a herbicid 0,10): jeden kanystr = 400 l přípravku. Herní model je v `docs/PLAN-koncentrat.md`.

**Koncentrát je vlastní druh plniva** (od 2026-10-11), ne vanilla `herbicide` / `liquidFertilizer`. `modDesc.xml` odkazuje na `xml/fillTypes.xml`
(kořen `<map>`, inline `<fillTypes>` modDesc.xsd nepřijme) s `SDT_CONCENTRATE_FERTILIZER` (Koncentrované hnojivo, 1,25 kg/l, 12 €/l) a
`SDT_CONCENTRATE_HERBICIDE` (Koncentrovaný herbicid, 1,10 kg/l, 13 €/l; hustota a cena jsou odhad z ceny kanystru); ikony
`hud/fillTypes/hud_fill_sdtConcentrate*.dds` jsou odvozené z obrázků kanystrů, jména mají cs/en překlady `fillType_sdtConcentrate*`. Nový druh
nesou kanystry (`objects/canister/*.xml`, i `multiPurchaseCanister*.xml`), sloty bedny a fill unit 3 vleku (hlavní nádrž se nemění). V `<mixer>`
mapuje `<ratio fillType="SDT_CONCENTRATE_*" product="herbicide|liquidFertilizer" concentrate="0.05"/>` koncentrát na hotový přípravek, který dron
skutečně nese (vanilla druh, nikdy koncentrát); `SprayDroneMixer.resolve` dostává mapu `products`, `getFillSource` vrací vždy produkt a
`takeFromTrailer` odebírá koncentrát podle `concentrateType` nádrže. Dávky, plánovač a trasa se nezměnily. Vanilla stanice a IBC koncentrátovou
nádrž neplní, jen kanystry z bedny nebo z ruky; staré savegame se sloty `HERBICIDE` / `LIQUIDFERTILIZER` se zahodí. Ve hře neověřeno.

**Zdroj přípravku pro dron** (`SprayDroneStation.getFillSource`, rozhoduje čistá `SprayDroneMixer.resolve`):

| hlavní nádrž | koncentrát | výsledek |
|---|---|---|
| hotový přípravek (`liquidFertilizer` / `herbicide`) | cokoli | **direct**: jako dosud, koncentrát se nepoužije |
| `water` | druh X (podíl `r` v `<mixer>`) | **mix**: dron dostane X, z vleku se na litr odebere `r` l koncentrátu a `1−r` l vody |
| `water` | prázdný / druh bez podílu | nic, hláška „chybí koncentrát“ (`STATUS_NO_CONCENTRATE`, v plánovači červeně) |
| prázdná | koncentrát | nic, hláška „chybí voda“ (`STATUS_NO_WATER`) |
| prázdná | prázdný | nic, „vlek prázdný“ (`STATUS_TRAILER_EMPTY`) jako dosud |

Dostupná zásoba = `min(voda / (1−r), koncentrát / r)` (`SprayDroneMixer.getAvailable`, vrací i omezující složku). Příklad:
`r` = 0,05, voda 300 l, koncentrát 50 l → min(315,8; 1000) = **315,8 l** (omezuje voda; spotřeba 300 l vody + 15,8 l
koncentrátu); jeden kanystr 20 l a voda 1000 l → min(1052,6; 400) = 400 l (omezuje koncentrát). Míchá se **při
plnění dronu**, ne předem: `pumpDrone` odebírá čerpadlem `litersPerSecond` z obou nádrží najednou (`takeFromTrailer`).
Během toho je `spec.isMixing = true` (server ho nastaví v `updateService`, jde po síti ve `writeState` hned za `isPumping`;
používá ho zvuk mixéru). F1: stav dronu „plní nádrž a míchá přípravek (60 l/min)“ a řádek „Míchání: 25 %
koncentrátu · voda … l · koncentrát … l“; varování „Hlavní nádrž je s vodou – chybí koncentrát“ (nebo chybějící voda) jen
když je vybrané pole, dron není plný a hlášení mise (status) totéž neříká samo (`getMixerText`).

**Plánovač**: řádek „Vlek: X l – voda“ (skutečný obsah hlavní nádrže), řádek „Koncentrát: X / 50 l – …“, při míchání „Míchání:
voda + koncentrát (25 % koncentrátu, 75 % vody) → Tekuté hnojivo“ a „K dispozici 200 l přípravku (omezuje koncentrát)“;
„k dispozici“ v litrech na postřik (`availableLiters`) počítá s tou namíchatelnou zásobou. `getRouteSummary` navíc vrací
`mainLiters`, `concentrateLiters`, `sourceKind`, `sourceReason`, `mixRatio`, `mixLimit`.

**Vypouštění dronu do vleku** (`Alt+1`, `TRANSFER_DRAIN_DRONE`): jen do prázdné hlavní nádrže, nebo když už obsahuje týž
přípravek (`getCanAcceptDrained`, `SprayDroneMixer.canAcceptDrained`); s vodou v nádrži se akce nenabídne, aby vanilla při
nízké hladině vodu potichu nepřepsala. Přečerpání vlek → IBC (`Alt+2`) posílá cokoli, co je v hlavní nádrži (i vodu, pokud
IBC vodu přijme).

**Ladění**: `.\tools\sdt_debug.ps1 -Command fillWater` (hlavní nádrž na plno vodou), `-Command fillConcentrate
[-ConcentrateType herbicide]` (koncentrát na plno, existující druh zůstane), `fillTrailer` (přípravek). Do zkušební hry
`python tools/prepare_testsave.py --water 800 --concentrate 40 [--concentrate-type herbicide]`. Čistou aritmetiku mixéru
zkouší `python tools/test_mixer.py`. Neověřeno ve hře (uzly `tankMain*` a `concentrateFillRootNode` přidá až export z Blenderu).

### Ukazatel naplnění (vpravo dole)

`getFillLevelInformation` (přepsaná funkce FillUnit) řadí řádky shora: **dron** „Nádrž (v dronu)" (u složeného vleku
„Nádrž (Dron zajištěn)"), „Baterie (v dronu)" v kWh varianty; **vlek** nádrž vleku, řádek **nabíječky** (dílky po
bateriích ve slotech, plné = připravené ≥ 95 %, vpravo „1 / 3“, titulek „Nabíjí 100/60/25 %“ nebo „Nabíječka …“) a
nafta. Bez dronu jen vlek. Ověřeno ve hře se 2, 3, 4 a 5 bateriemi — s pěti se titulek „Nabíjí 92/66/33/22 %“ ještě
vejde. F1 ukazuje jen plánovač letu, start / návrat (když jdou) a jeden řádek dronu (stav, pole, dávky); nabíječka a centrála jsou jen ve vleku bez dronu.

### Zajištění dronu na plošině

Dron je součást i3d vleku (uzel `<prefix>Root` pod vizuálem hlavní komponenty) bez vlastní fyziky ani kloubu, takže se
za jízdy ani při převrácení vleku fyzicky oddělit nemůže: pohybuje se s komponentou jako kterýkoli jiný díl modelu.
Odpojí ho jen skript při vzletu (`link(getRootNode())`) a po přistání ho vrátí (`attachDrone`); vzlétnout jde jen z
rozloženého vleku, složit vlek jde jen s dronem v doku. Ve hře ověřena jízda se složeným vlekem ~36 m rovně pomalu
(dron na plošině); rychlá jízda, zatáčky a převrácení ověřené nejsou (plyne to z toho, že dron nemá fyziku).

Vizuální zajištění (od 2026-10-23): úchyty lyžin jsou součást plošiny, ne dronu, a nezávisí na variantě. Na každé straně jedna
překlápěcí příčka (`padClampL/R`: černý pant a sedlo, `padClampHingeL/R`: žlutá příčka 12 × 40 cm s gumovým podkladem a
ocelovým čepem), která zakrývá lyžiny všech velikostí (S, M, L mají lyžiny 0,34 / 0,42 / 0,56 m od osy; příčka sahá přes
0,26 až 0,665 m od osy) a je posunutá o 11,5 cm podél lyžin vedle příčky mezi lyžinami. Jsou součástí animace `foldLadder`:
2–2,4 s (po složení dronu, souběžně s vyklopením žebříku) se příčka překlopí o 100° přes lyžiny, při rozkládání se v tomtéž
úseku otevře. **Viditelné jsou jen se zcela složeným dronem** (`unfold <= 0`); jakmile se dron začne rozkládat, zmizí. Na
plošině bez dronu nejsou (Lua `loadDroneService`: uzly `padClampL/R` + přípona `2` u druhé plošiny). U Mini se nestaví: dron
tam drží bedna.
Pod dronem je na plošině heliport (tmavý kruh, bílé mezikruží a „H“, vrstvy s `decalLayer`). Stav „Dron zajištěn" (čas skládání ≥ `securedFoldTime`) ukazuje ukazatel
naplnění u nádrže dronu (viditelný z tahače; do složeného vleku nastoupit nejde). Příčky jsou jen vizuál, nemají
kolizi ani fyziku.

### Čáry ve světě

`SDT_TOGGLE_LINES` (`Alt+5`, ve vleku) skryje a znovu zobrazí všechny čáry, které mod kreslí ve světě: kruh dosahu,
obrys vybraného pole, trasu po dávkách, přelety a letovou plochu. Výchozí stav je zapnuto, stav je jen lokální
(`SprayDroneStation.showWorldLines`, neposílá se ani neukládá, po restartu hry je zase zapnuto). Plánovač se nemění.

### Zvuk

`sounds/droneRotorLoop.ogg`: smyčka rotorů (mono, 44,1 kHz, 8,9 s, bezešvá), vzorek `vehicle.sprayDrone.sounds.rotor`
(schéma `SoundManager.registerSampleXMLPaths`), načtený `g_soundManager:loadSampleFromXML` jen u klienta, 3D
připojený k `<prefix>Tilt` varianty (letí s dronem; každý blok `<drone>` má vlastní vzorek), `innerRadius` 8 m, `outerRadius` 120 m, venku hlasitost 1,2, uvnitř 0,6
s dolní propustí. Hraje, dokud se vrtule točí; výška `(0,45 + 0,55 × otáčky) × rotorPitch` (S 1,25, M 1, L 0,8; log ve hře
„zvuk 1.25“ u S) a hlasitost `otáčky^0,7` (otáčky 0..1)
jdou přes `setSamplePitchOffset` a `setSampleVolumeScale` (přímé `setSamplePitch/Volume` by `SoundManager:update`
přepsal). Roztočení (2 s) i doběh (4 s) je tak slyšet. Otáčky plynou ze stavu letu, takže klient zní stejně.
`DEBUG_SOUND = true` vypisuje otáčky, výšku a hlasitost do logu.

**Zvuky vleků** (od 2026-10-13, Pavel: ne jedna dlouhá neurčitá smyčka): u Middle a Max zmizela smyčka skládání (`<fold>`); ramena a listy dronu cvaknou při rozkládání
(`droneUnfoldStep`, vanilla `hingeSmall`) a skládání (`droneFoldStep`, `clackVar2`) vždy při překročení jednoho z pěti prahů `spec.unfold` (`SprayDroneSound.UNFOLD_STAGES`,
driver `droneUnfoldStage`, u dvou dronů platí nejdál rozložený). Žebřík při pohybu skřípe (`metalDoorSqueaksSmall` v `foldLadder`) a na koncích cvakne (`clackVar1`), úchyty lyží a víko truhly
zacvaknou (`latchSmall`, `coverMetalOpen`, `metalClose`), víka kapes navíječů (Max) zaklapnou po úchytech lyží, baterie se zasune s `clickLong`. Mini dál používá smyčku skládání (celá
posloupnost bedny je ve skriptu). **Neslyšeno ve hře** (vzorky jsou vanilla šablony, hlasitosti jsou odhad).

Zdroj: „Big Slow Heavy Drone Hovering Idle Loop“, qubodup, https://freesound.org/people/qubodup/sounds/854382/,
**CC0 1.0** (odvozeno z CC0 nahrávky DJI Mavic Mini 2 od Sadiquecat, https://freesound.org/people/Sadiquecat/sounds/683298/).
Stažen HQ náhled bez přihlášení, výška snížena na 3/4, smyčka uzavřena crossfadem 0,6 s (`out/tmp/zvuk/make_loop.py`).
Licence a úpravy jsou v `mod/FS25_SprayDroneTrailer/sounds/LICENSE.txt`.

**Další zvuky vleku** (`SprayDroneSound.lua`, vzorky jsou vanilla šablony v `<sounds>` bloku `<sprayDrone>`, bez vzorku vlek mlčí): smyčky `pour` (nalévání
z kanystru do koncentrátové nádrže / elektrocentrály, `defaultRefuelSound`, hraje, dokud z kanystru teče, `tb.pouring` ve stavu vozidla), `groundDrain`
(vypouštění na zem Ctrl+I, `riceFieldWater`), `fold` (skládání a rozkládání vleku po dobu animace, `foldMoveDirection ~= 0`, `slidingGateMetalLoop`; platí
pro panely i žebřík všech tří vleků, protože ty se hýbou podle času skládání) a `door` (roleta skříně, `rollingGarageDoor`, hraje, dokud se hýbe),
jednorázové `boxOpen` / `boxClose` (víko Mini `metalOpen` / `metalClose`, vrata skříně `latchSmall` / `metalClose`; spustí se při změně počtu otevřených beden).
Voda ve vlece hraje vanilla `waterTrailer` (`<waterTrailer><sounds><refill>`). Zvuk slyší jen klienti v dosahu vzorku (`innerRadius` / `outerRadius`).

### Světla dronu

Na straně každého ramene u motoru je pouzdro s kulatou čočkou zapuštěnou do předního okraje (`<prefix>Led_i`, součást
`build_drone.py`, dívá se šikmo dolů a ven od trupu; pod motorem je náboj spodní vrtule nebo tryska): vpředu vlevo **červená**
(rameno 1), vpředu vpravo **zelená** (rameno 2), vzadu obě **bílé** (3, 4), jako orientační světla DJI Agras. Přední svítí
trvale, zadní blikají 1 Hz (0,5 s svítí, 0,5 s ne), dokud je dron zapnutý: letí nebo se točí vrtule (tedy i roztáčení na plošině a doběh
po přistání). Složený a stojící dron má LED zhasnuté. Stav plyne ze stavu letu a otáček vrtulí, takže je stejný
u serveru i klientů (fáze blikání z `g_time`, mezi hráči se může lišit).

- **Svit**: materiál `SDT_NavLed` je vanilla `vehicleShader` s variantou `staticLight_vertex`: barva svitu je v barvě
  vrcholů sítě (export z Blenderu, atribut `Col`), intenzitu dává parametr `lightIds0.x`, který skript nastavuje
  `setShaderParameter` (0 = zhasnuto, `navLights#intensity` = svítí). `export_middle_mod.py` materiál přepisuje sám
  (`EMISSIVE_MATERIALS`).
- **Světlo**: před každou čočkou je bodové světlo (Blender Point → i3d `Light`, dosah 3 m, bez stínů; exportér má
  zapnuté `i3D_exportLights`). Svítí jen s LED **a jen když dron není na vleku a je aspoň 2 m** (`LED_LIGHT_MIN_HEIGHT`)
  nad plošinou, takže nenasvítí vlek do červena. Ověřeno v noci s L: na plošině tma, po vzletu dron nasvícený.
- Destičky na lyžinách (`NavLight_L/R`) zrušeny (2026-10-23), lyžiny jsou bez světel.

### Žebřík (Middle a Max)

Sklopný žebřík na **pravém boku** (−X), zavěšený nahoře z boku; Middle i Max ho staví týž kód (`build_ladder` v `build_trailer_middle.py`, Max mění jen
`LADDER_HINGE_Y`, `LADDER_FOLD_DIR` a výšku čepu). Mini žebřík nemá. **Složený leží vodorovně podél boku těsně pod horní deskou** (kolejnice v rovině boku,
horní kolejnice končí těsně pod nápisem na boku), **rozložený se jen sklopí dolů o 90° kolem čepu na horním konci** (`ladderHinge`, osa X kolmá na bok) a visí
svisle dolů; žádné vysouvání ani náklon, lezení z boku.

- **Poloha**: osa kolejnic `LADDER_SIDE_X` = −(`TOP_W`/2 + 0,09) = −1,14 m (9 cm vně rámu: konzola s čepem, vodítko hadice u předního rohu vyčnívá ~7 cm),
  rozteč kolejnic `LADDER_W` 0,38 m, čep `LADDER_HINGE_Z` = `POST_TOP` − `LADDER_HINGE_DROP` 0,20 (Middle 2,13, Max 2,41), spodek rozloženého žebříku
  `LADDER_FOOT_Z` 0,25 m nad zemí (delší by se při sklápění otočil do předního krytu kola; spouštěč lezení sahá až k zemi). Po Y: Middle `BASE_Y0` + 0,40 (y −1,70,
  přední roh hned za pravou přední nohou y −2,02, před vodítkem hadice y −1,57), složený leží od čepu dozadu (`LADDER_FOLD_DIR` +1, y −1,7 až 0,2); Max y 1,75 (před
  předním blatníkem tandemu), složený leží od čepu dopředu (−1, y −0,4 až 1,75). Pevná je jen konzola na boku horního nosníku (deska, válcový čep).
- **Madla** (kloub `ladderGrab`, sourozenec `ladderHinge` ve stejném čepu, rozteč `LADDER_GRAB_W` 0,26 m): rozložená míří svisle nahoru 0,75 m nad horní desku,
  při skládání se sklápí **opačným směrem** o 90° a leží vodorovně podél složeného žebříku uvnitř jeho výšky (nic nevyčnívá nad desku ani před vlek).
- **Skládání** (`foldLadder`): klouby `ladderHinge` a `ladderGrab` 2–2,6 s z 3 (viz „Rozložení dronu s vlekem“), s `ladderHinge` jede kolize i spouštěč lezení.
- **Kolize** `colLadder`: tenký kvádr v rovině žebříku (šířka žebříku + 4 cm za kolejnicemi, tloušťka 10 cm), od čepu dolů po 25 cm nad zemí
  (`LADDER_COL_MIN_Z`), dítě `ladderHinge` (složený leží vodorovně u boku). Skupina a maska stejné jako u ostatních kolizí vleku (`0x10004` / `0xfe3ffb83`).
- **Lezení**: spouštěč `ladderTrigger` (vanilla `LadderTrigger`, `SprayDroneLadder.lua`) je před žebříkem **vně vleku** (od osy 0,75 m ven, 0,20 m dovnitř k x −0,94, šířka
  žebříku + 5 cm na každé straně, od 5 cm nad zemí do 0,7 m nad čep), dítě kloubu. Je zapnutý jen u zcela rozloženého vleku (`ACTIVE_UNTIL` 0,05, Lua beze změny).
  Hráč přijde z boku a leze čelem k vleku, nahoře přestoupí přes okraj desky mezi madly.
- **Ověřeno v Blenderu** (`blender/check_ladder.py -- middle|max`): žádný průnik pohyblivých dílů (děti `ladderHinge` a `ladderGrab`) s ostatními díly vleku (kola, kryty kol,
  blatníky, navíječ, hadice, nohy zasunuté i vysunuté o `LEG_TRAVEL`) v mřížce 11 × 11 poloh obou kloubů (tedy při libovolném vzájemném časování), nejmenší vzdálenost 2 mm
  (čep a konzola, konstrukční dotyk).
- **Neověřeno ve hře**: nastoupení z boku (poloha a velikost spouštěče, 25 cm nad zemí začíná první příčka), `colLadder` v přístupu, přestup na desku, chování u zapřaženého vleku v zatáčce.

### Náklon vleku (Middle a Max)

Vlek nemá nohy a nevyrovnává se (od 2026-10-14/15, Pavel: „kašleme na nožičky“). Rozložit jde jen vlek, který stojí dost rovně: blok `<tilt max="5"/>` v XML vleku,
`scripts/SprayDroneLevel.lua` (`checkDeploy` z `getIsFoldAllowed`, hláška `sdt_warning_tilt`). U složeného vleku ukazuje `drawTilt` v nápovědě řádek „Náklon vleku: podélně … · příčně … (nejvýš 5°)“,
čísla zeleně v mezi a červeně mimo. Test: `python tmp/f/test_level.py`. Mini nemá `<tilt>` a má vlastní kontrolu plošiny (`SprayDronePad.checkDeploy`).

### Efekt postřiku

Vlastní částicový efekt `effects/sprayMist.i3d` (generuje ho `python blender/build_spray_mist.py`, bez Blenderu; emitor je
malý čtyřúhelník s normálou dolů, 4 vrcholy + UV, `meshUsage` 260 = CPU mesh + příznak emitoru, tedy volby tvaru
`0x01040003` jako ve vanilla efektech; bez příznaku emitoru a UV hra hlásila `Particle System emitter mesh ... could not
be loaded`. Nastavení částic je psané ručně, protože exportér GIANTS částice nezná). Tři emitory pro varianty (`0|0` S,
`0|1` M, `0|2` L) se liší poloměrem kužele u země (S 2,3, M 3,4, L 4,5 m); částice letí z trysky dolů rychlostí
odvozenou z výšky postřiku a stranou podle poloměru, takže tvoří kužel od dronu až k zemi, a zůstávají ve světě, takže
za dronem zůstane stopa. Vzhled: `psSubUVShader` s kouřovým atlasem `smoke6x6`. Barvu podle přípravku dává `setSprayMistColor`
(parametr `colorAlpha` shaderu na uzlu částic, při každém startu emise podle `droneFillType` daného dronu, takže po
změně náplně platí od další dávky; tabulka `MIST_COLORS` podle jména druhu): tekuté hnojivo zelená (0,55 0,85 0,25),
herbicid modrá (0,40 0,62 1,0), vápno (`LIME`, `SDT_FINE_LIME`) bílá a hustá, voda šedomodrá a řidší, jiný nebo neznámý
přípravek bílá. Čtvrtá složka je hustota (alfa: vápno 1,6, voda 0,7, ostatní 1; `psSubUVShader` snese do 4). Chyba
parametru mlhu jen nechá bílou.

`<drone>.effects` varianty: `effectNode` (`effectClass="ParticleEffect"`, `filename="effects/sprayMist.i3d"`,
`linkNode="<prefix>Tilt"`, jeden na trysku) a `nozzleY` (výška emitoru pod kloubem náklonu). Skript
(`placeSprayEffects`) je při prvním startu postaví pod trysky: uzly, `effects.nozzle#x/#z` (S a L, dvě trysky
vzadu / na rameni postřiku), jinak pod motory ramen (M, 4). Záběr ošetřené plochy (`workWidth`) se tím nemění.

Běží, jen když dron opravdu stříká (waypoint `spray`, náplň > 0, drženo 150 ms); stav `sprayEffectsActive` jde v
`writeState`, takže klienti efekt pouštějí sami (`updateSprayEffects`).

Ladění: `SprayDroneStation.DEBUG_FORCE_MIST = true` nechá dron bez vzletu a bez spotřeby jezdit tam a zpět 16 m
dlouhou dráhou 8 m vpravo od vleku ve 3 m nad zemí, s vrtulemi a mlhou (`debugMistLoop`).

Spotřeba: vanilla `Sprayer:getSprayerUsage` = `litersPerSecond × rychlost[km/h] × záběr` za sekundu, tedy na metr
dráhy `litersPerSecond × 3,6 × záběr` (tekuté hnojivo i herbicid 0,0081 l/s → ~292 l/ha, 0,26 l/m při 9 m). `usageScale` 0,2 spotřebu zmenšuje na ~58 l/ha
(0,052 l/m při 9 m), takže nádrž 40 l vystačí na ~770 m řádku (~0,7 ha); při `usageScale` 1 to bylo ~150 m.

## Ovládání

Schéma (2026-10-29, `docs/OVLADANI-audit.md`, sekce Provedeno): **R = věc ↔ objekt**, **levé tlačítko = použít držený nástroj nebo
kliknout na ovladač stroje**, **B = zapnout / vypnout stroj**, **X = složit vlek**, **Alt+číslo jen mise a přečerpání**. Všechno jde přes
InputAction (respektuje přemapování), žádné `Input.isKeyPressed` ani surové `keyEvent` / `mouseEvent`.

Pěšky:

| klávesa (akce) | co dělá |
|---|---|
| `R` (`ACTIVATE_OBJECT`) | plošina: nasadit / sundat dron; šachta: vložit / vyndat baterii; držák pumpy a tyče: uložit / vyndat (tyč se sama neukládá); hadice: vzít, připojit, pustit, odpojit; nalít z kanystru; bedna: nabídka kanystrů; kufr: víko nebo baterie (viz níž); tyč: rozložit / složit. R s tabletem v ruce funguje u objektů normálně, tablet sám R nepoužívá. |
| levé tl. (`ACTIVATE_HANDTOOL`) | tablet v ruce: plánovač; displej vleku: plánovač; víko bedny; tlačítko rozvaděče mlýnku; páka ventilu mlýnku (hadice / roura); kloub výsypné roury mlýnku; opěry násypky; vstup pumpy (nádrž / rybník); bednička vzorků v kufru (míří se na ni): odeslat vzorky |
| `B` (`SDT_TOGGLE_FOOT`) | pumpa, násypka, mlýnek (rozvaděč), elektrocentrála vleku (u výfuku, `GENERATOR_DISTANCE` 1,6 m), tyč (rozložená) |

Ve vozidle:

| akce | klávesa | kdy jde |
|---|---|---|
| Dron: plánovač letu (`SDT_OPEN_PLANNER`) | `Alt+7` | ve vleku (složený vlek: hláška `sdt_planner_folded`) |
| Dron: spustit let (`SDT_START_FLIGHT`) | `Alt+8` | ve vleku; pole je vybrané, mise neběží |
| Dron: návrat na vlek (`SDT_RETURN_HOME`) | `Alt+0` | ve vleku; mise běží nebo dron letí |
| Pohled z dronu (`SDT_DRONE_VIEW`) | `Alt+9` (`C` přepíná z dronu / na dron) | ve vleku, dron má kameru |
| Čáry ve světě (`SDT_TOGGLE_LINES`, text skrytý) | `Alt+5` | ve vleku |
| Vypustit nádrž dronu do vleku (`SDT_DRAIN_DRONE`, text jen když jde) | `Alt+1` | vlek i tahač; dron na plošině rozloženého vleku; znovu = stop |
| Přečerpat nádrž do IBC (`SDT_PUMP_TO_PALLET`, text jen když jde) | `Alt+2` | vlek i tahač; IBC do 6 m; znovu = stop |
| Koncentrát do kanystrů (vanilla `TOGGLE_TIPSTATE_GROUND`) | `Ctrl+I` | vlek i tahač |
| Elektrocentrála zap./vyp. (vanilla `IMPLEMENT_EXTRA`) | `B` | ve vleku, nebo z tahače s vybraným vlekem |
| Mlýnek: motor (`IMPLEMENT_EXTRA`) / výstup (`IMPLEMENT_EXTRA3`) | `B` / `Y` | ve vozíku, nebo z tahače s vybraným vozíkem |
| Složit / rozložit vlek (vanilla Foldable) | `X` | ve vleku nebo z tahače |

Plánovač: `Enter` start, `Esc` zavřít, `Space` návrat, `End` restart pole (u vzorkovače odeslat vzorky), `X` kreslení, `C` zpět,
`Backspace` smazat plochu, `Q` / `E` nastavení, `PageUp` / `PageDown` další dron (tlačítko „Dron:“, ve všech režimech otevření).

**Kdo dostane stisk pěšky.** `ActivatableObjectsSystem` nabízí jen jednu aktivaci, tu s nejmenší `getDistance`; vzdálenosti se měří
k uzlu, kterého se akce týká (šachta, plošina, hrdlo, spojka, držák), a když hráč na ten uzel míří (`SprayDroneLink.isAimedAt`, osa kamery
do 0,35 m), počítá se o 1,5 m blíž (`SprayDroneLink.aimDistance`). Text nápovědy je vždy text té jedné vybrané aktivace. Displej vleku
(levé tl.) a centrála (B) jsou vlastní akce v kontextu hráče: s vybranou aktivací se porovnají (`isSelectedCloser`) a vyhraje bližší,
druhá akci nepřijme ani neukáže (`SprayDroneLink.mayClick` / `mayToggle`). Kliky ustupují zvedání předmětu, na který hráč míří, a nefungují
s tabletem nebo předmětem v ruce. **Kufr:** R vyndá baterii, jen když na ni hráč míří (0,25 m) nebo u ní stojí do 0,6 m
(`SprayDroneBatterySlots.CASE_TAKE_DISTANCE`, `getIsCaseReach`); jinak R ovládá víko a aktivace víka se při vyndávání baterie nenabízí.

**B a cizí mod:** `SDT_TOGGLE_FOOT` se registruje s `disableConflictingBindings` (`SprayDroneLink.registerToggle`), protože FS25_handTools
drží na `B` v kontextu hráče natrvalo `HANDTOOL_TAKE`; neúspěch registrace se jednou zaloguje. Ladicí příkaz `inputInfo` vypíše, co
na klávesách modu teď leží.

Levý panel nápovědy ve vleku je schválně krátký: Alt+5 je skrytý, Alt+1 / Alt+2 jen když jdou (`SprayDroneStation.updateActionEventStates`).

Textové řádky pod nápovědou (`drawHudTexts`): jeden řádek dronu „Dron: na vleku · pole 4 · dávek: 5“ (bez pole „Dron: na vleku ·
pole nevybráno (Alt+7)“); přečerpávání, míchání a hlášení mise (status) přibudou jen, když se to děje. Vlek bez dronu: „Vlek bez
dronu (dokup ho v dílně)“ a řádek s nabíječkou a centrálou.
`Alt+5` a `Alt+6` ve hře s ničím nekolidovaly (ve vleku i v pickupu: jen text akce se přepne, vanilla na `5` / `6`
v těchto vozidlech nic nemá); v nastavení ovládání se konflikt nekontroloval. **`Alt+1` / `Alt+2` kolidovaly s osou
tempomatu** (vanilla `1` / `2` v pickupu, ve hře 120 → 119 → 117 km/h), když akce modu byla neaktivní. Proto jsou
akce modu (i `Alt+8`, `Alt+0`) pořád aktivní a jen se skryjí z nápovědy, když nejdou; stisk pak nic neudělá a tempomat
se nemění (ověřeno: 2× `Alt+1` v pickupu, tempomat zůstal 120).

### Plánovač letu

Celoobrazovková herní mapa (stejná jako v menu mapy, s ikonami vozidel a čísly polí), při otevření přiblížená
tak, aby se na výšku vešlo zhruba 2,8× dosah, a vycentrovaná na vlek vlevo od panelu. Posun tažením myši,
zoom kolečkem.

- **Vlek**: oranžový čtvereček s popisem VLEK (vedle vanilla ikony vozidla). **Dron** ve vzduchu: azurový
  čtvereček.
- **Kruh dosahu**: azurová kružnice o poloměru dosahu. Dosah = nejdelší přímý přelet, kdy tam s plnou nádrží ve výšce
  přeletu (se stoupáním) a zpět prázdný + rezerva 30 s vystačí na plnou baterii; zaokrouhleno dolů na 10 m, strop
  `maxRange` podle varianty: S 600 m, M 900 m, L 1200 m (výchozí 1500 m z `<sprayDrone>` platí jen pro variantu bez
  vlastní hodnoty). Z baterie vychází S 3,6 km, M 3,3 km, L 2,6 km, takže vždy platí strop varianty (kruh se s výškou
  přeletu nemění; na okraji dosahu zbývá v baterii velká rezerva).
- **Rozložení (od 2026-10-23, jako herní mapa; návrh a rešerše `docs/NAVRH-planovac-ui.md`)**: mapa přes celou plochu, vlevo
  tmavý sloupec se záhlavím „PLÁNOVAČ LETU“ a panelem z herních prvků GUI (`fs25_subCategoryContainer`, profily jako
  vanilla mapa, Courseplay a AutoDrive), vpravo nahoře karta plánu, dole herní lišta tlačítek. Panel má nahoře přepínač
  stránek s tečkami (jako „Druhy plodin“, `pageSelector`):
  - **Pole**: seznam (`SmoothList`) polí v dosahu, kam dron smí (vlastní a přijaté zakázky; ikona zeleně / zlatě), a dalších
    vlastních polí; řádek ukazuje nejnaléhavější nález skenu (plevel, zralé, bez vápna, nehnojeno) a stáří mapy. Klik pole
    vybere a posune na něj mapu (nahradil tabulku „Přehled polí“). Bez vybraného pole nemá seznam zvýraznění. Prázdný seznam
    napíše `sdt_ui_noFieldsNear`.
  - **Mise** a **Let**: nastavení jako herní volby úlohy pomocníka (`MultiTextOption` profil `fs25_aiCreateJobMultiTextOption`
    po skupinách: Druh mise; Přelet, Pole, Drony – jen u dvou dronů) místo řádků s − / +. Šipky u volby mění hodnotu,
    nepovolená volba je šedá. `Q` / `E` mění vybranou (naposled kliknutou, výchozí první na stránce) volbu; na stránkách Pole
    a Mapa tytéž klávesy listují stránkami (tlačítka dole se přejmenují). Klávesy obsluhuje `SprayDronePlannerScreen:inputEvent`
    dřív než `ScreenElement` (ten by s prvkem `pageSelector` listoval po svém), volby samy `Q` / `E` ignorují.
  - **Mapa skenu**: seznam jako legenda herní mapy (`fs25_mapList`, barva ve čtverci položky): vrstvy mapy skenu (klik zvolí,
    zvolená zeleně), barvy zvolené vrstvy (nenaskenováno, vybledlé) a „Trasa a dosah“ (barvy čar mapy; nahrazuje dlouhý text
    legendy).
- **Karta plánu** (`scripts/gui/SprayDronePlannerCard.lua`, kreslí se v `draw()` nad herními prvky): štítek PLÁN LETU, pole
  velkým písmem, druh a přípravek; varování jako barevné štítky (červené = nejde letět, oranžové = pozor, zelené = hotovo,
  fialové = letová plocha); dlaždice 2 × N s bílými ikonami (`tools/make_ui_icons.py`, `gui/icons/ui*.dds`): dávky, čas letu,
  plocha, potřeba / zásoba (u skenu buňka a výška), nafta, baterie na dávku a výměny, přelet (výška a délka), vítr / limit;
  pod nimi podrobnosti (servis a čekání, výdrž baterie, přelety tam a zpět), zelený blok úspory podle skenu, souhrn mapy
  skenu a stav vleku (nádrže, míchání, drony, baterie, centrála, dron, dosah, nejvyšší bod). Když se karta nevejde, vynechá
  podrobnosti a stav vleku zkrátí na dva řádky.
- **Mapa**: obrysy všech polí v dosahu (vlastní zeleně, zakázky zlatě, kam dron nesmí šedě), vybrané silně zeleně, pod kurzorem
  bíle s bublinou u kurzoru (název, druh nebo důvod, „Kliknutím ho vybereš“). Hlášky a návod kreslení plochy jsou pruh nahoře
  uprostřed volné části mapy. Při otevření je střed mezi vlekem a vybraným polem ve volné ploše mezi panelem a kartou.
- **Ladění** (`SprayDroneDebug.plannerCommand`): `plannerReload` načte znovu XML a skripty plánovače bez restartu hry
  (`tmp/ui.ps1 -Reload` je zkopíruje do `_reload/<n>/`, protože `source()` stejný soubor podruhé nespustí a `loadfile` hra
  nemá), `plannerMiddle`, `plannerPage1..4`, `plannerLayout` (polohy prvků v pixelech okna pro skutečné kliky).
- Ověřeno ve hře (2026-10-23, Max i Middle, 1600 × 900 a 1920 × 1080): skutečné kliky myší na přepínač stránek, volby
  (mise, aplikace, úvratě), řádek seznamu polí a vrstvu mapy; `Q` / `E` na stránce Let, `X` kreslení plochy, bublina nad
  polem, karta při postřiku, skenu, dešti a na prázdné plošině. Neověřeno: gamepad, šipky nahoru / dolů mezi volbami
  (fokus se neposune), multiplayer, rozlišení 21 : 9.
- **Překážky u dráhy**: červené body s výškou v m (po buňkách 12 m nejvyšší); s bočním odstupem 15 m jich na poli 2
  přibude. Přelety bílé čárkované po skutečné zaoblené dráze, přejezdy mezi řádky tenkou čarou (půlkruhy).
- Řádek „Dron malý / střední / velký: nádrž, baterie kWh × ks“; bez baterií červeně „nemůže vzlétnout“.
- **Klik na pole** ho vybere (příkaz jde přes event na server, jako dřív `Alt+7`). Když vybrat nejde, důvod se
  ukáže v panelu. Za letu pole změnit nejde.
- **Trasa**: řádky vybraného pole, barva čáry = číslo dávky. Za letu se každých 5 s přepočítá, takže hotové
  řádky mizí.
- **Přelety**: bílé čárkované čáry z vleku k začátku každé dávky a z konce zpět, po skutečné cestě (s letovou plochou
  lomené).
- **Tlačítka** dole: `Enter` Spustit let (jen když je vybrané pole a je co dělat), `Mezerník` Návrat domů (jen
  když mise běží nebo dron letí), `X` Kreslit / Upravit letovou plochu, `Backspace` Smazat plochu (jen když
  nějaká je), `Esc` Zavřít. Plánovač se sám zavře, když hráč z vleku vystoupí nebo se vlek složí.
- **Přepínání dronů (2026-10-29, ve hře neověřeno)**: tlačítko „Dron: <vlek / kufr – vzdálenost, stav> (n/m)“ a `PageUp` /
  `PageDown` fungují ve všech třech režimech otevření (`SprayDronePlannerScreen.MODE_*`); přepnutí plánovač znovu otevře pro
  nový cíl se stejným režimem. Cíle (`SprayDroneLink.getPlannerTargets`):
  - **tablet**: vleky a kufry farmy s dronem ve spojení s hráčem (`getTabletTargets`, poloha hráče); plánovač hlídá spojení hráče
    s ovládaným cílem, výchozí cíl je naposled použitý.
  - **ve vleku (`Alt+7`) a z displeje**: stejné pravidlo, jen místo hráče platí domov vleku, ze kterého se plánovač otevřel
    (origin, `getStationTargets`): vleky a kufry s dronem, jejichž rádio (nebo relé s nimi spojené) origin pokrývá; origin je v seznamu
    vždy, i bez dronu. Dál platí podmínka originu (sedět v něm a rozložený / stát u jeho displeje). Když cíl spojení ztratí
    (`isStationTargetConnected`), plánovač blikne NO CONNECTION a vrátí se na origin. Displej se nabízí i u vleku bez dronu (jako `Alt+7`).
  - **Mapa**: ovládaný vlek / kufr a jeho drony ve vzduchu azurově (barva kruhu dosahu), ostatní cíle bíle s číslem pořadí z
    tlačítka; klik na ikonu jiného cíle na něj přepne. Legenda „Trasa a dosah“ má oba řádky. Velká mapa hry se nemění
    (značka dronu jen za letu, barva podle čísla dronu): s otevřeným plánovačem není vidět a jinak nic „ovládaného“ není.
  - **Max se dvěma drony** je jeden cíl: plánovač ovládá oba najednou (volba „Drony v misi“, trasy po dronech barvou), dron 1 / 2
    se nepřepíná.
  - Složený vlek / zavřený kufr (z tabletu): karta červeně „Vlek je složený“ / „Kufr je zavřený“, start vrátí tutéž hlášku
    (`SprayDroneStation.getFoldedWarning`; dřív server start tiše zahodil a plánovač napsal „Let spuštěn“). Platí i pro `Alt+8`.
  - Ladění: `plannerOpen` (jako `Alt+7` ve vozidle, pěšky nejbližší vlek / kufr bez podmínky nástupu), `plannerOpen 1..9` (N-tý vlek
    / kufr farmy z `plannerInfo`), `plannerNext` / `plannerPrev` (`PageDown` / `PageUp`), `plannerInfo` (režim, origin, cíl, seznam);
    `tabletNext` přepíná v otevřeném plánovači v každém režimu. Test bez hry: `python tools/test_tablet.py`.

### Letová plocha

Mnohoúhelník, ve kterém se dron smí pohybovat při přeletech vlek → pole, pole → vlek (i při návratu domů), aby
obletěl budovy a stromy dvora místo přeletu nad nimi. Patří k vleku **a k poli**: každé pole má svou plochu, při
dalším výběru pole se načte.

- **Kreslení**: vybrat pole, `X` (Kreslit letovou plochu). Klik do mapy přidá vrchol, pole se v tomhle režimu
  nevybírá, tažení dál posouvá mapu. Rozkreslená plocha je růžová s čarou ke kurzoru; první bod se u kurzoru zvětší
  a klik na něj plochu uzavře (nebo `X` Uzavřít plochu, jde od 3 bodů). `C` smaže poslední bod, `Esc` kreslení
  zruší (uložená plocha zůstane), `Backspace` smaže celou plochu. Nejvýš 64 bodů. `X` u pole, které plochu má,
  otevře úpravu: body se převezmou a dají se odebírat od konce a přidávat.
- **Hotová plocha**: fialová výplň a obrys (jiné barvy než pole a trasa), ve světě fialová debug čára 1 m nad terénem.
- **Povolená oblast = plocha ∪ pole.** Vlek smí stát v ní nebo nejvýš 6 m (`HOME_TOLERANCE`) za jejím okrajem.
  Plánovač hledá nejkratší cestu z vleku k začátku každé dávky a z jejího konce zpět: graf viditelnosti nad lomovými
  vrcholy plochy i pole a průsečíky jejich hranic, Dijkstra od vleku (plocha i pole smí být nekonvexní). Úsek
  grafu je povolený, když každý jeho kus mezi průsečíky s hranami leží uvnitř plochy nebo pole (tolerance 0,5 m).
  Přesuny mezi řádky v dávce letí nad polem jako dosud, přímo.
- **Výška**: každý úsek cesty má vlastní výšku, nejméně `corridorHeight` (8 m), a kontrola překážek raycasty
  (`getClearHeight`) ji zvedne, když je v pásu úseku něco vysokého. Na lomu do vyššího úseku dron vystoupá na
  místě, do nižšího klesá za letu. Pojistka za letu běží dál.
- **Když cesta není** (vlek mimo plochu, plocha nesahá k poli, nespojitá plocha), souhrn to červeně napíše („Vlek
  stojí mimo letovou plochu" / „Letová plocha nespojuje vlek s polem"), trasa se nevykreslí a Spustit let nejde,
  dokud se plocha neopraví nebo nesmaže. Kdyby se to stalo až za mise, mise skončí se stavem „letová plocha
  nespojuje vlek s polem".
- **Bez plochy** se letí jako dřív: přímo, ve výšce nad překážkami (nejméně `transitHeight`).
- **Odhady**: čas dávky (baterie) i souhrn počítají s celou lomenou cestou (zastavení a otočení na každém lomu,
  stoupání na vyšší úsek). Při plánování délky řádku se návrat odhaduje shora přes začátek nebo konec řádku (cesty
  z nich se pamatují), skutečný návrat dávky se počítá přesně. Kontrola baterie za letu (každý snímek) bere cestu
  plochou z paměti po 10m buňkách.
- **Návrat domů** za letu jde také plochou (z bodu zabrzdění, s tolerancí 50 m k okraji); když cesta není, přímo.
- **Ukládání a síť**: `saveToXMLFile` → `flightArea(fieldId).point(x, z)` pod `sprayDroneStation` ve `vehicles.xml`.
  Uzavření i smazání plochy jde eventem `SprayDroneAreaEvent` z klienta na server, server ji rozešle ostatním
  klientům; nový hráč dostane všechny plochy v `onReadStream`. Trasu si každý počítá sám.

### Úvratě

Nastavení letu `headlands` (0–4 kola po obvodu pole, výchozí 0 = dosavadní chování) a `headlandFirst` (1 = začít úvratěmi,
0 = začít řádky, výchozí 1; s 0 úvratěmi nemá význam a řádek je šedý). Jde stejnou cestou jako ostatní nastavení
(`SprayDroneStation.SETTINGS`, `SprayDroneSettingsEvent`, `flightSettings`); u výběru má položka `values` (překlady hodnot)
a `requires` (nastavení, které musí být nad nulou).

- **Geometrie** (`SprayDroneRoute.offsetPolygon`, `getHeadlandLoop`, `buildHeadlandLegs`): úvrať i (i = 1 je nejvnější) je
  uzavřená smyčka v odstupu d = (i − 0,5) × `workWidth` od hranice, tedy pruh šířky záběru přiléhá k pruhu úvratě i − 1
  (nebo k hranici). Smyčka je offset polygonu pole s mitrovým spojením rohů; u vrcholů, kde se hranice lomí od pole a mitr by
  přesáhl `HEADLAND_MITRE_LIMIT` (2 × d), je vrchol nahrazen obloukem o poloměru d po 30°. Části smyčky mimo pole nebo blíž
  než `HEADLAND_MIN_DISTANCE` (0,9) · d k hranici se při vzorkování vynechají. Hrany smyčky jsou legy, začátek je vrchol
  nejblíž vleku, směr ten, kde konec první hrany leží blíž vleku. Ořez kruhem dosahu a výběr workable/covered jako u řádků.
- **Řádky** se omezí na vnitřek: úsek řádku, jehož střed leží blíž hranici než `headlands` × `workWidth`, se nevyrobí
  (`appendNeededParts` s `nearestBoundaryPoint`), takže se s úvratěmi nepřekrývají.
- **Pořadí**: `headlandFirst` = 1: úvratě 1..n (vnější první), pak řádky; 0: řádky, pak úvratě n..1 (vnější poslední).
  Plánovač dávek (`planBatch`) nepředpokládá boustrophedon: mezi libovolnými dvěma legy použije `rowTurn` (smyčka s oblouky,
  jinak ostrý přejezd v `sprayHeight`), takže skok z konce smyčky na řádek nebo do další smyčky funguje. Nově: když další leg
  začíná v místě konce předchozího (`CONTINUE_DISTANCE` 0,5 m, roh smyčky), `rowTurn` vrátí prázdný přejezd a `planBatch`
  spočítá jen rychlost průjezdu rohem a otočení na místě (nad `TURN_STOP_ANGLE` 30° dron v rohu zastaví). Rohy se tedy
  nezaobloují, dron na nich zpomalí; plocha a litry v souhrnu jdou ze všech legů (řádky jsou ořezané, nepočítají se dvakrát).
- **Paměť**: záznam pole má navíc `hl` (počet úvratí při zápisu) a `headlands[i]` = intervaly oblouku s po smyčce i (s = délka
  od začátku smyčky, který je nezávislý na vleku: první vrchol offsetu). `markCovered(all, field, type, ww, headlands, x1, z1, x2, z2)`
  zapíše úsek, jehož střed je blíž hranici než `headlands` × ww − `HEADLAND_ROW_SLACK` (1 m), do úvratě
  floor(vzdálenost / ww) + 1 (nejbližší body smyčky k okrajům úseku, u přesahu přes začátek smyčky se interval rozdělí), jinak
  do řádku. Text v `#coverage`: `pole/druh/záběr/hl/řádky/úvratě` (`k:od,do,…|k:…`), starý formát se nečte. Změna `hl`,
  druhu postřiku nebo záběru záznam zneplatní. `coverField` v `SprayDroneDebug` zapíše `headlands[i] = {{-1e9, 1e9}}` a aktuální `hl`.
- **Zkouška**: `python tools/test_headlands.py` (LuaJIT/lupa, čistá geometrie: offset, mitr a oblouk, pořadí, paměť, `planBatch`).
  Ve hře neověřeno.

### Chování

- **Kruh dosahu ve světě**: azurový „plot" (čáry ve výšce 0,5 m a 4 m se sloupky) kolem vleku, vybrané pole
  obtažené zeleně a trasa jako debug čáry. Debug čáry mají hloubkový test, takže za stromy a za kopcem vidět
  nejsou.
- **Trasa** (s úvratěmi viz **Úvratě**): řádky rovnoběžné s nejdelší hranou pole, rozteč `workWidth`, začíná se od strany bližší vleku, směr
  se střídá (boustrophedon). Řádky se ořežou kruhem dosahu a vynechají se místa, kde by vanilla postřik nic
  nezměnil (mimo pole a farmland, plodina ve stavu sklizně, hnojivo: už postříkáno tímto typem nebo maximální
  `sprayLevel` – na Riverbend Springs je max 2; herbicid: plevel, na který herbicid nepůsobí).
- **Let**: dron je rozložený s vlekem; na plošině jen roztočí vrtule (2 s), teprve pak vzlétne
  do výšky přeletu úseku (sekce Překážky), přeletí na začátek dávky, klesne na `sprayHeight`, letí řádky, stoupne,
  vrátí se, přistane na vleku, servis (plnění čerpadlem, výměna baterie pod 30 %, případně čekání na nabití), další
  dávka. Mezi dávkami
  i po misi vrtule jen doběhnou a dotočí se do klidové polohy; složí se až s vlekem. Dávka končí, když by nádrž
  nebo baterie (včetně cesty zpět a rezervy) nestačila.
  Po posledním řádku zůstane dron na vleku a hlásí „pole je hotové". Před každou dávkou se znovu ověří, že pole
  jde ošetřovat; když zakázka mezitím skončila, mise se ukončí s hláškou „pole už ošetřovat nejde".
- **Dynamika**: rychlost se mění plynule (`acceleration`), na každém waypointu dron zpomalí podle úhlu k dalšímu
  úseku (rovně = plnou rychlostí dál, pravý úhel a víc = zastavit). Vzlet zrychluje až na `ascentSpeed` a u výšky
  přeletu brzdí; klesání na plošinu u země zpomaluje (0,35 + 0,5 × zbývající metry m/s), takže dosedne měkce.
  Na konci řádku zabrzdí, otočí se (yaw s omezenou rychlostí a zrychlením otáčení, dokud je odchylka nad 30°,
  letí jen 1,5 m/s), přejede na další řádek a zase zrychlí. Nos míří po směru letu, při klesání na vlek se srovná
  se směrem vleku. Uzel `Drone_A_Tilt` naklání dron podle rychlosti a zrychlení (rozjezd ~10°, cestovní rychlost
  ~5°, brzdění dozadu), klient ho počítá sám z interpolované polohy.
- **Zaoblení a profil (0.8)**: rohy přeletů jsou oblouky (poloměr ≤ `cruise²/turnAcceleration`, strop 15 m), na řádek
  dron přilétá a z něj odlétá po jeho směru přes bod 8 m před / za řádkem (řádek se nezkracuje), přejezd mezi řádky je
  půlkruh za koncem řádku (u 9 m r = 4,5 m, ~3,3 m/s, bez zastavení). Svisle: vzlet jen 2 m nad plošinu, pak stoupání
  za letu (sklon 0,45), klesání za letu (0,27), domů do 3 m nad plošinu a svislé přistání. Ve hře (log `SDT t=…`):
  na otočce u konce řádku v neklesne pod ~1,2 m/s a nos se natáčí plynule, na přeletu h roste s v 6 m/s.
- **Odhady**: plánování dávek (baterie) i souhrn v plánovači počítají s rozjezdem a brzděním na každém waypointu,
  otáčením, stoupáním `ascentSpeed` a pomalým dosednutím. Změřeno ve hře (pole 2): odhad letu dávky 100 / 110 /
  129 s proti skutečnosti 97 / 108 / 122 s, tedy o 2–6 % opatrnější. Souhrn přičítá roztočení a servis.
- **Návrat**: dron zabrzdí po směru letu, vystoupá do výšky přeletu úseku k vleku, vrátí se a přistane; mise se
  zastaví. Další start pokračuje jen po neošetřených místech (trasa se vždy počítá ze stavu pole). Start během
  návratu misi obnoví: dron dosedne, doplní se a letí dál. Návrat ještě na plošině (během roztáčení) nevzlétne.

### Překážky

- **Plánování**: každý přeletový úsek (vlek → začátek dávky, konec dávky → vlek, návrat) se projede po ~5 m po
  **skutečné zaoblené dráze** svislými paprsky shora (`raycastClosest` od terénu + 120 m dolů) v pásu
  `droneRadius` + boční odstup (výchozí 1,6 + 4 = ±5,6 m, po ≤ 1,2 m napříč). Maska
  `STATIC_OBJECT + TREE + BUILDING` (0x1802): terén ani vozidla (vlastní vlek, tahač) do ní nepatří, dron kolize nemá.
  Výška přeletu úseku = max(nejvyšší překážka + `obstacleClearance`, `transitHeight`; s letovou plochou
  `corridorHeight`), cesta plochou má výšku pro každý svůj úsek. Pak se ve zvolené výšce
  pás proletí vodorovnými paprsky; co svislé paprsky minuly (kmen a větve stromů mezi vzorky), výšku zvedne
  po 2 m. Výsledky se pamatují podle úseku a nejnižší výšky. Plánovač ukáže nejvyšší výšku přeletu všech dávek,
  žlutě „kvůli překážkám v cestě", když je nad `transitHeight` (s plochou nad `corridorHeight`).
- **Limit**: překážka, kvůli které by přelet musel nad `maxTransitHeight` (60 m), dávku zablokuje: plánovač napíše
  „Překážka v cestě převyšuje limit 60 m – přeparkuj vlek", Spustit let nejde (u první dávky) a mise se u takové
  dávky ukončí se stavem „v cestě je překážka".
- **Pojistka za letu**: při vodorovném pohybu (ne při přistání) letí každý snímek 5 paprsků přes celou šíři dronu
  (s přídavkem 0,3 m) ve dvou výškách (0,2 a 0,8 m nad lyžinami) po dráze dopředu (i do oblouku) na brzdnou dráhu + 4 m.
  Ve hře 0.9 (pole 2 s L, odstup 4 m) nezasáhla ani jednou. Při zásahu dron zabrzdí, stoupá, dokud paprsek neprojde, a ještě 2 m; pak letí dál
  o tolik výš a klesá zpět, až pod ním nic není. Na poli (postřik ve 3 m) se překážky řeší jen touto pojistkou.
  Ve hře na poli 2 zasáhla u stromů na dvoře farmy, které plánování nezachytilo (1× za 2 dávky po zhuštění pásu,
  předtím 5×), a vystoupala o 2,6–10 m.
- **Složení vleku** (X z auta) za letu: nesloží se, zobrazí se varování a dron se vrací. Rozjetí vleku
  rychleji než 3 km/h za letu vyvolá totéž. Složení během doplňování misi ukončí.
- Vystoupení z vleku let nepřeruší.
- **Volno nad plošinou před vzletem** (`scripts/SprayDroneLaunch.lua`, `getClearance`): 17 svislých `raycastAll` nahoru
  (střed, 8 bodů na kruhu `droneRadius` + 0,3 m a 8 na jeho polovině, od 0,3 m nad dronem do max(`transitHeight`, 12 m))
  s maskou `STATIC_OBJECT + TREE + BUILDING + PRECIPITATION_BLOCKING + VEHICLE + DYNAMIC_OBJECT` a `overlapBox` nad plošinou
  (stejný kruh × celá výška, `STATIC_OBJECT + TREE + BUILDING`) na větve mezi paprsky. Vlastní souprava a triggery se
  přeskakují. Důvod podle skupiny zasaženého uzlu: `TREE` strom, `BUILDING` nebo `PRECIPITATION_BLOCKING` (ne vozidlo)
  střecha / most, jinak překážka; z víc zásahů se hlásí nejhorší. Start letu (klient) pro každý dron v misi vrátí
  hlášku „Dron nemůže vzlétnout: nad ním je střecha nebo most / strom / překážka“; server před každou dávkou
  (`startNextBatch`) při zásahu nečeká na konec mise, ale jako u relé tyče čeká na plošině (`waitingForClearance`,
  HUD „čeká na volný prostor nad plošinou“) a zkouší to po 5 s znovu. Plánování přeletu proto sloup nad plošinou
  (do `droneRadius` od domova) nepočítá, jinak by střecha nad vlekem zvedla celý přelet nebo ho zablokovala.
  Ladění: `takeoffCheck` vypíše výsledek a zásahy (paprsek / box, uzel, skupina, výška) pro drony cílového vleku.

**Výběr pole pohledem kamery byl zrušen.** Mapa ukazuje totéž přehledněji (dosah, všechna pole, důvod, proč
pole nejde), funguje i na pole za kopcem nebo za stromy, kam kamera nedohlédne, a dvě cesty k výběru by znamenaly
dva kódy, které se musí chovat stejně. `Alt+7` proto teď otevírá plánovač; `Alt+8` a `Alt+0` zůstaly jako
rychlé akce (návrat domů byl do 0.4 na `Alt+9`, to ale koliduje s vanilla `9` = přepnutí mapy).

## Jak je to postavené

- `scripts/SprayDroneStation.lua` — specializace vozidla: stavy `PARKED / FLYING / RETURNING / SERVICING`,
  let po waypointech (rychlost s rozjezdem a brzděním, yaw, pojistka `getIsPathBlocked`), postřik, doplnění,
  vizuál dronu (`updateDroneParts`: rozložení, vrtule, náklon), HUD, akce, ukládání, síť. Pro plánovač:
  `getFieldAllowed` (vlastní pole / zakázka / dosah / přípravek, vrací i důvod a zakázku), `selectField`,
  `startFlight`, `getRouteSummary`, `refreshRoutePreview`, `getTransitHeight` (výška přeletu úseku s pamětí).
  Letová plocha: `setSprayDroneFlightArea` (s eventem), `getCorridor` (graf plochy vybraného pole a vleku, přepočítá
  se při změně plochy, pole nebo posunu vleku o 1 m), `getHomePath` (cesta na vlek s pamětí), `getTransit` (přelet
  mezi vlekem a bodem: body, výška každého úseku, délka; bez plochy přímý úsek).
  `DEBUG_FLIGHT = true` zapíše do logu každých 0,5 s polohu, rychlost, výšku, yaw a náklon, u každé dávky body
  a výšky přeletu tam a zpět, odhad a skutečný čas.
- `scripts/SprayDroneRoute.lua` — geometrie bez vozidla: polygon pole, pole pod bodem, řádky, ořez kruhem,
  vzorkování „potřebuje postřik" (krok 2 m), časy přesunů (`moveTime`, `landingTime`, `turnTime`), raycasty
  překážek (`getClearHeight`), letová plocha (`newCorridor`, `setCorridorHome`, `getCorridorPathHome`: graf
  viditelnosti a Dijkstra; `transitTime`, `appendTransitWaypoints`: čas a waypointy lomeného přeletu), plánování
  dávky (`planBatch`) a rozpad na dávky pro zobrazení.
- `scripts/gui/SprayDronePlannerScreen.lua` + `gui/SprayDronePlannerScreen.xml` — plánovač jako `ScreenElement`
  (načte se při prvním otevření přes `g_gui:loadGui`, otevírá `g_gui:showGui`). V XML je vanilla prvek
  `InGameMap` s profilem `ingameMapOverview` (jako `InGameMenuMapFrame` a Courseplay), napojený na HUD mapu
  `g_currentMission.hud:getIngameMap()`. Obrysy, kruh a trasa se kreslí v callbacku `onDrawPostIngameMap`
  (`drawLine2D`), panel a popisky v `onDrawPostIngameMapHotspots` (`drawFilledRect`, `renderText`). Převod
  svět → obrazovka stejně jako `IngameMap:drawHotspot` (`mapExtensionScaleFactor/Offset` a
  `fullScreenLayout:getMapObjectPosition`), obrazovka → svět přes `IngameMapElement:getLocalPosition` a
  `localToWorldPos`. Tlačítka jsou vanilla profily `buttonOK`, `buttonActivate`, `buttonBack`, `buttonMenuSwitch`
  (`MENU_EXTRA_1` = X), `buttonActivate` s `inputAction="MENU_EXTRA_2"` (C) a `buttonDelete` (`MENU_CANCEL` =
  Backspace) v `fs25_buttonBox`; viditelnost a texty se mění podle režimu (`updateButton`, `invalidateLayout`).
  Panel a lišta tlačítek jsou pro mapu „cursor deadzone", takže klik do nich pole nevybere. `IngameMapElement`
  volá `onClickMap` jen při kliku bez tažení, takže posun mapy v režimu kreslení body nepřidává. Výplň plochy jsou
  vodorovné `drawLine2D` po 3 px.
- `scripts/events/SprayDroneCommandEvent.lua` — příkaz z klienta na server (výběr pole, start, návrat).
- `scripts/events/SprayDroneAreaEvent.lua` — letová plocha pole (fieldId + až 64 bodů float32, prázdná = smazat)
  z klienta na server a od serveru ostatním; `writeArea` / `readArea` používá i `onWriteStream` / `onReadStream`.
- Postřik: každé ~2 m dráhy `FSDensityMapUtil.updateSprayArea` na rovnoběžník široký `workWidth` (stejné volání
  jako `Sprayer:processSprayerArea`, typ z `g_sprayTypeManager:getSprayTypeByFillTypeIndex`), jen když střed úseku
  projde kontrolou přístupu (vlastní pozemek nebo `getIsMissionWorkAllowed`). Litry se odečítají z nádrže dronu,
  statistiky `sprayedHectares` a `sprayUsage` vlastníkovi pozemku.
- Multiplayer: let, postřik i doplnění běží jen na serveru; výběr pole a start jdou eventem a server je znovu
  ověří. Klient dostává stav, pole, náplň, baterii a polohu dronu přes `onWriteUpdateStream` (dirty flag každý
  snímek letu) a polohu vyhlazuje. Nový hráč dostane stav v `onWriteStream`. Trasu k zobrazení si klient počítá
  sám ze synchronizovaných density map; zakázky (`field.currentMission`, `farmId`, stav) synchronizuje hra.
  Rozložení, vrtule, náklon a zvuk se po síti neposílají: rozložení plyne z času skládání vleku (synchronizuje
  Foldable), vrtule ze streamovaného stavu (`FLYING/RETURNING` = roztočit, jinak doběh a dotočení do klidu) a náklon
  z polohy, takže je server i klient počítají stejně. Server při startu dávky nechá dron na vleku (připojený),
  dokud se neroztočí; klient vidí totéž.
- Ukládání (`vehicles.xml`, `FS25_SprayDroneTrailer.sprayDroneStation`): `fieldId`, `missionActive`,
  `droneFillLevel`, `droneFillType`, `generatorEnabled`, `battery(i)#level/#slot`, `flightSettings#headlands/#headlandFirst/#transitHeight/
  #obstacleClearance/#sideClearance` a `flightArea(i)#fieldId` s `point(j)#x/#z`; varianta a počet baterií jsou vanilla
  `configuration`. Když byla mise aktivní, dron po načtení stojí na vleku a za 3 s sám pokračuje zbytkem pole
  (ověřeno ve hře 0.9 s L a 5 bateriemi).

## Bedna a kanystry

Bedna vleku (`scripts/SprayDroneToolbox.lua`, event `scripts/events/SprayDroneToolboxEvent.lua`) má až **48 slotů** po 20 l
(`slots` v XML, výchozí 15; Middle 48, Max 48, Mini 2 × 4; uzly `toolboxCanister1..N`). Kanystry jsou **skutečné herní objekty kupované v obchodě** (viz „Kanystr jako
kupovaný objekt“ níž; tři druhy: koncentrát tekutého hnojiva, koncentrát herbicidu a nafta) a hráč je **unese v rukou** (`supportsPickUp`, levé tlačítko myši, otáčení
prostředním tlačítkem – vanilla `HandToolHands`). Slot je buď **volný** (`FillType.UNKNOWN`), nebo drží uložený kanystr
`{fillType, litry}`. Kanystr, který hráč podrží nad **otevřenou** bednou, si bedna vezme (objekt zmizí, obsah se
zapíše do slotu); **prázdný** kanystr (zmizí sám) ani kanystr nad 20 l (cizí naftový do 25 l) bedna nevezme; z dialogu bedny se kanystry **vyberou**
(ze slotů vzniknou nové objekty za vlekem). **Nafta je jen další druh kanystru**: žádný slot není vyhrazený, kterýkoli pojme koncentrát i naftu a bedna
s naftou zachází stejně jako s koncentrátem (vsátí jen u otevřeného víka / vrat, řádek v dialogu, výdej, stejný otvor, stejné místo výdeje); jediný rozdíl je kam se
z kanystru lije. **Nalévání z kanystru** je ruční: kanystr v ruce se nakloní víčkem dolů nad hrdlo koncentrátové nádrže (fillUnit 3,
`SprayDroneStation.getConcentrateUnit`, `concentrateNeckNode`) nebo, je-li naftový, nad hrdlo elektrocentrály (`dieselNeckNode`); totéž přes R (viz „Nalévání z kanystru přes R“ níž).
Koncentrátová nádrž se dá **vypustit** do nových kanystrů (tím se mění koncentrát). Kanystry se z palet / IBC
**neplní**. Herní model: `docs/PLAN-koncentrat.md`.

**Bedna nemá žádné vlastní klávesy**: obsluha používá jen vanilla mechanismy, tedy aktivaci objektu (`R`) a vanilla dialogy.

**XML** (`<sprayDrone>` v šabloně, všechny atributy nepovinné, uzly jsou i3dMapping jména):
`<toolbox lidNode="toolboxLid" openAngle="105" slots="12" slotLiters="20" activateNode="toolboxActivateNode"
canisterNodePrefix="toolboxCanister" neckNode="concentrateNeckNode"/>`; navíc `lidTime` (1,2 s), `activateDistance` (4 m), `spawnDistance` (2,0 m od středu bedny, kam se vybraný / vypuštěný kanystr postaví) a `spawnSign` (1 dopředu / -1 dozadu podél osy Z vozidla; bez něj od středu vleku pryč; Mini má `spawnDistance="1.9" spawnSign="-1"`),
otvor pro vsátí `intakeHalfWidth` (1,05 m po X vozidla), `intakeHalfLength` (0,75 m po Z), `intakeBelow` (0,35 m), `intakeAbove`
(0,9 m) kolem `toolboxActivateNode`, nalévání rukou `pourRadius` (0,3 m) a `pourRate` (4 l/s), vypouštění koncentrátu na zem
`groundDrainRate` (4 l/s) a u skříně `doorTravel` (m, o kolik roleta `Toolbox_Door` po otevření vyjede vzhůru; bez atributu se panel jen zmenší `scale.y`). `openAngle` je ve stupních **se znaménkem** (víko se otočí kolem lokální osy X uzlu
`lidNode`, zavřeno je původní natočení). Kód je nil-bezpečný: bez `toolboxLid` se víko neanimuje, bez `toolboxCanisterN` se
nebarví, bez `toolboxActivateNode` se vzdálenost měří od kořene vleku.

**Skříň na kanystry (Middle a Max)**: jedna bedna přes všech 48 slotů, místo víka rolovací vrata (`doorNode="Toolbox_Door"`, žádný `lidNode`; pivot nahoře uprostřed otvoru). Roleta se při otevření **nesmršťuje do nuly, ale vyjede nahoru**:
`SprayDroneToolbox.applyLid` posune pivot po ose Y rodiče o `doorTravel` × t (Middle i Max 0,302 m = od horní hrany otvoru po strop skříně minus rezerva 4 cm,
`cabinet_door_travel`) a zároveň zmenší jeho `scale.y` z 1 na `DOOR_ROLLED_SCALE` 0,2 (panel 1,39 m → 0,28 m), takže po otevření leží celý nad otvorem v pouzdře roletové
schránky (`build_cabinet_housing`: čelní krycí plech, válec s boky a žebra v dutině mezi horním patrem a stropem, nad `Toolbox_DoorRail`). Konečná poloha panelu leží
2,2 cm pod stropem a 1,2 cm nad horní hranou kolejnice, nic z pouzdra ani stropu neprotíná (kontrola BVH v 5 krocích otevření); zakrytý je celý, jen válec pouzdra
zasahuje do jeho zadní strany a okraje panelu končí v postranních stěnách (vodicí drážky). Obě skříně staví týž kód (`build_canister_cabinet`):
4 patra × 2 řady × 6 kanystrů na výšku (`toolboxCanister1..48` odspodu po patrech, v patře od zadní stěny k vratům, v řadě po X), zadní stěna u nádrže, vrata na samém konci
vleku (`cabinet_y_range`; Middle y 1,84…2,26, Max y 6,08…6,50), popisky na panelu vrat, kolize `colToolboxFloor` přes celý půdorys. `toolboxActivateNode` leží u vrat
uprostřed výšky otvoru a otvor pro vsátí (`intakeBelow/Above` 0,7 m, ±1,05 m po X, ±0,75 m po Z) pokrývá celý otvor vrat. Middle i Max mají skříň stejně vysokou: nad horním patrem plný strop až pod horní plošinu (`cabinet_ceiling`), žebřík je na boku a skříň mu
nepřekáží. Nafta má v obou stejný slot, dialog i vsátí jako koncentrát.

**Víc samostatných beden** (Mini): vnořené `<box lidNode= activateNode= firstSlot= slotCount= openAngle=/>` v `<toolbox>` (nejvýš 4; `MAX_BOXES`).
Každá bedna (`tb.parts[i]` v kódu) má vlastní víko (`open`, `lidT`, časovače), referenční bod, aktivaci, dialog, otvor pro vsátí a **jen svůj
rozsah slotů** (`getSlotRange(tb, fillType, part)`: výběr, volný slot, skupiny v dialogu i vypouštění nádrže se dívají jen do něj). Bez `<box>` vznikne
jedna bedna přes všechny sloty s `lidNode` / `activateNode` / `doorNode` / `openAngle` z `<toolbox>` — Middle a Max se chovají beze změny. Příkazy
`OPEN`/`CLOSE`/`TAKE`/`DRAIN` nesou číslo bedny v události (`BOX_BITS` 2), stav víka každé bedny a číslo bedny posledního vsátí jdou ve `writeState`.
Kanystr nad otvorem patří bedně, jejíž otvor ho obsahuje (otvory se nepřekrývají); kanystry se vyrábějí vedle bedny, ze které se vybíralo.
Víc aktivací vedle sebe vybírá vanilla podle `getDistance` (nejbližší referenční bod), takže u pravé bedny je pravá, u levé levá.

**Ovládání bedny** (klient, `SprayDroneToolboxActivatable`, vanilla `ActivatableObjectsSystem`, do `activateDistance` od
`toolboxActivateNode`, jen pro farmu, která smí k vozidlu). Aktivace si registruje dvě akce (`registerCustomInput`, jako vanilla dveře):
1. **Klik levým tlačítkem myši** (`ACTIVATE_HANDTOOL`, ve vozidle se bedna neovládá): „Otevřít bednu“ / „Zavřít bednu“, bez dialogu. Víko zůstane
   otevřené, dokud ho hráč nezavře (samo se nezavírá, ani po čase, ani když hráč odejde; stav otevřeno se ukládá do savegame, `toolbox.part(i)#open`). Klik nereaguje, když hráč něco drží (patří rukám: pustí
   to) nebo míří na zvednutelný předmět (kanystr) – to je stejná akce, kterou používá `HandToolHands`.
2. **R** (`ACTIVATE_OBJECT`): „Kanystry v bedně“, vanilla **`ObjectStorageDialog`** jako u skladu objektů — řádek i počet v jednom
   okně (u vleku s víc bednami jen sloty bedny, u které hráč stojí): „Tekuté hnojivo – kanystr“ / „Herbicid – kanystr“ (počet do kolika je v bedně) a „Herbicid – z nádrže“ (vypustí koncentrátovou
   nádrž do nových kanystrů, počet = kusy po 20 l; delší text se do výběru nevejde). Přelévání ze slotů rovnou do nádrže v dialogu **není** (Pavel 2026-10-03) — do nádrže se lije
   jen z kanystru v ruce. Bez řádků (prázdná bedna i nádrž) jen hláška. Dialog víko neovlivňuje.

**Vsátí kanystru** (jen server, `updateIntake` každých 0,5 s, jen u **otevřené** bedny s volným slotem mezi jejími sloty, stejně pro koncentrát i naftu): vezme se kanystr
z modu (`configFileName` končí `canisterFertilizer.xml` / `canisterHerbicide.xml` / `canisterDiesel.xml`, `spec_pallet`; z cizích módů i pallet s jedinou naftovou nádrží do 25 l, ten se
ale kvůli kapacitě slotu 20 l nevsaje), který
- je v **otvoru bedny**: kvádr v souřadnicích vozidla kolem `toolboxActivateNode` (`intakeHalf*`, `intakeBelow/Above`; `getIntakeDistance`),
- patří farmě vleku,
- **nenese jiný objekt** (dynamic mount, upínací pásy),
- není čerstvě vyrobený bednou: takový kanystr nese `sdtEjectTime` a vsaje se až poté, co jednou opustí otvor, hráč ho vezme do rukou
  nebo uplyne 20 s (`EJECT_PROTECT_MS`).

**Kanystr v ruce hráče se vsaje také**: server ho nejdřív hráči z rukou vezme (`player.hands:dropHeldItem()`, pošle vanilla
`HandsThrowObjectEvent`) a pak smaže (`vehicle:delete()`). Obsah (druh + litry, i 0 l) jde do prvního volného slotu, do stavu vozidla se
zvýší počítadlo vsátí (`storeCounter`) a klient poblíž (10 m) dostane vanilla notifikaci „Kanystr uložen do bedny (druh)“.

**Nalévání rukou** (`updatePour`, server každých 0,1 s; `findPourCanisters`): kanystr z modu, jehož víčko (`canisterCap` z i3d kanystru)
je do `pourRadius` (0,3 m) od `concentrateNeckNode` (naftový od `dieselNeckNode`) a ne víc než 8 cm pod ním a jehož osa míří dolů (svislá složka ≤ 0,2, tj. naklonění
přes ~78°), vylévá látku do koncentrátové nádrže `pourRate` l/s (při větším náklonu rychleji, až 4 l/s). Jde to s kanystrem v ruce
i s volným. Nalít jde, jen když je nádrž prázdná nebo obsahuje týž druh a není plná. Jinak klient, který kanystr drží, dostane
hlášku s důvodem (jednou za 4 s, `updatePourHint`). Prázdný kanystr zmizí (`removeVehicleIfEmpty="true"` v xml kanystru, jako u vanilla palet).

**Napouštění vody** je vanilla `waterTrailer` (typ vozidla `sprayDroneTrailer` má specializaci `waterTrailer`, v XML `<waterTrailer fillUnitIndex="1"
fillLitersPerSecond=…>` s vanilla zvukem `defaultRefuelSound`): R u vodní plochy napouští hlavní nádrž (fillUnit 1) jen tehdy, když je kořen vleku
(výchozí `fillNode`) nejvýš 0,2 m nad hladinou, tj. vlek stojí u vody (rybník, řeka, jezero); nic „z ničeho“. Jde jen do prázdné nádrže nebo s vodou.
Rychlost Mini 150 / Middle 300 / Max 500 l/s.

**Vypouštění koncentrátu na zem** (Ctrl+I, vanilla `TOGGLE_TIPSTATE_GROUND`): akci registruje `SprayDroneStation` (i z tahače se zapřaženým vlekem), je
aktivní a vidět jen tehdy, když je v koncentrátové nádrži (fillUnit 3) co vypustit. Vanilla `Dischargeable` kapaliny na zem vypustit neumí
(`getCanDischargeToGround` chce density map height type, který kapaliny nemají), proto vlastní stav `tb.groundDrain` (příkazy `GROUND_DRAIN_START` /
`GROUND_DRAIN_STOP`, ve stavu vozidla): server odečítá `groundDrainRate` l/s z nádrže, dokud není prázdná nebo to hráč znovu neodklepne; příkaz se
ověřuje jen na farmu, ne na vzdálenost od bedny (hráč sedí v tahači). Vizuální efekt (stružka) zatím není, jen zvuk a úbytek ve fillUnit 3.

**Příkazy** (`SprayDroneToolbox.command`, server / hostitel; klient bez serveru je pošle `SprayDroneToolboxEvent` s
`command` (3 bity), `fillType` a `count` (4 bity)):

| příkaz | co dělá |
|---|---|
| `OPEN` / `CLOSE` | víko (stav `open` jde ve `writeState`) |
| `TAKE druh N` | až N kanystrů daného druhu se vyrobí jako nové objekty za vlekem; slot se uvolní až po úspěšném vytvoření |
| `DRAIN N` | z koncentrátové nádrže N nových kanystrů po 20 l (poslední může být částečně plný); okamžitě |
| `GROUND_DRAIN_START` / `GROUND_DRAIN_STOP` | vypouštění koncentrátové nádrže na zem (Ctrl+I) |

**Server ověřuje** (`isConnectionAllowed`): hráč z tohoto spojení smí k vozidlu a je do 8 m od bedny. Příkaz hostitele se neověřuje.

- **Vypustit nádrž**: koncentrát se dělí na kusy po 20 l. Kusy jdou nejdřív do volných slotů bedny, další se vyrobí jako objekty za
  vlekem. Bez volného slotu a bez kanystrového xml v obchodě se akce odmítne.
- **Nic se neztratí**: při vybrání je slot zamčený (`spawning[slot]`), dokud se objekt nevytvoří. Při vypouštění se litry odebírají
  těsně před uložením; když se objekt nevyrobí, litry se vrátí do nádrže (jinak do slotu) a do logu jde varování.

**Jak se objekt kanystru vyrábí** (`spawnCanister`, jen server): `VehicleLoadingData` s cestou `objects/canister/canister*.xml`
(musí být v `<storeItems>`), kontrola limitu palet (`slotSystem`), místo **za zadním koncem vleku mimo otvor bedny** (řada po šesti po
0,4 m, `spawnDistance` od středu bedny ve směru `spawnSign`, další řady o 0,4 m dál, výška terén + 0,2 m; leží-li střed bedny víc než 0,3 m
od osy vleku, jako u Mini, řada se rozbíhá do strany bedny od 0,4 m, takže kanystry nevzniknou ani pod vysunutou deskou, ani u oje), `spawnEmpty`, obsah se doplní
`addFillUnitFillLevel`, nastaví se `sdtEjectTime`.

**Multiplayer.** Dialog běží na klientovi, výsledek jde jako příkaz přes event; sání, vybrání, nalévání, voda a litry dělá jen server.
Stav (`open`, `pouring`, `watering`, počítadlo vsátí, `fillType` a `litry` slotů) jde ve `writeState` / `readState` vozidla.

**Kolize** (`build_trailer_middle.equipment_collisions`): bedna, elektrocentrála, koncentrátová nádrž (jen tělo, hrdlo zůstává volné),
čerpadlo, mixér a navíječ mají neviditelné kolizní kvádry (`colToolbox`, `colGenerator`, `colInductionTank`, `colPump`, `colMixer`,
`colHoseReel`, compoundChild, skupina vozidla). Hlavní nádrž má kolizi podle velikosti (`colTank800/1000/1500/3000/5000`), přepíná ji
`objectChange compoundChildActive/Inactive` stejně jako viditelnost `tankMainNNN`.

**Barva kanystru v bedně** (`colorScale`): hnojivo `0,55 0,8 0,15`, herbicid `0,85 0,25 0,08`, prázdný šedý; model je vidět jen
ve slotu, který ho drží.

**Ukládání**: `vehicles.xml` → `sprayDroneStation.toolbox.canister(i)#fillType/#liters` (víko se po načtení zavře). Vyrobené
kanystry jsou samostatné objekty ve světě.

**Ladění** (`tools/sdt_debug.ps1 -Command …`, příkaz dostanou všechny vleky, vozidlo u hráče se pozná podle kamery):
`toolboxFill`, `toolboxOpen`, `toolboxDialog`, `spawnCanister`, `spawnAtCamera` (kanystr 2,4 m před kamerou; dosah zvednutí rukou je
2 m), `pickCanister`, `holdCanister`, `dropHeld`, `dropOnBox` (kanystr přímo do otvoru), `tiltCanister` (8 s nakloněný nad hrdlem),
`probeTarget` (co vidí zaměřovač rukou), `status` (hladiny a stav bedny do logu), `fillWater`, `fillConcentrate`.

**Ověřeno ve hře (2026-09-30):** zvednutí kanystru rukou (hmotnost 1 kg, limit rukou 0,2 t, dosah 2 m), otevření bedny aktivací,
dialog včetně listování šipkami, vsátí volného kanystru do otevřené bedny, vybrání kanystru (objeví se za vlekem a nevrátí se),
nalití nakloněného kanystru do hrdla nádrže (20 l přeteklo), napouštění vody (R), puštění kanystru z rukou serverem.
**Neověřeno:** vsátí kanystru přímo z ruky hráče nad otvorem (zvlášť vsátí a zvlášť puštění z rukou fungují), ruční naklonění
prostředním tlačítkem myši, multiplayer, kolize hráče na palubě.

### Kanystr jako kupovaný objekt

Dvě položky v obchodě (kategorie `pallets` + `palletFertilizerHerbicide`, značka LIZARD, v modDesc `<storeItems>`), vanilla typ
vozidla `pallet` (bez vlastní specializace):

| soubor | název | látka | cena |
|---|---|---|---|
| `objects/canister/canisterFertilizer.xml` | Koncentrované hnojivo – kanystr 20 l | `LIQUIDFERTILIZER` | 60 € |
| `objects/canister/canisterHerbicide.xml` | Koncentrovaný herbicid – kanystr 20 l | `HERBICIDE` | 90 € |

- **Rozpoznání v Lua**: `vehicle.configFileName` končí `objects/canister/canisterFertilizer.xml` / `canisterHerbicide.xml`
  (`vehicle.customEnvironment` je mod), `vehicle.spec_pallet ~= nil`, `vehicle.typeName == "pallet"`.
- **Obsah**: fillUnit **1**, kapacita **20 l**, jediný povolený fillType (viz tabulka), kupuje se plný (`startFillLevel="20"`;
  objekt spawnovaný kódem přes `VehicleLoadingData` bude taky plný, obsah je nutné dorovnat `addFillUnitFillLevel`). Prázdný
  kanystr se nemaže (`removeVehicleIfEmpty` není zapnuté). Čtení `getFillUnitFillLevel(1)`, `getFillUnitFillType(1)`,
  `getFillUnitCapacity(1)`; změna `addFillUnitFillLevel(farmId, 1, deltaL, fillTypeIndex, ToolType.UNDEFINED)`.
- `fillTriggerVehicle` (uzel `fillTrigger`, 20 l/s) dovoluje čerpat z kanystru jako z palety; `dynamicMount` a `tensionBeltObject`
  jako u vanilla palet. Hmotnost 1 kg (`updateMass="false"`, obsah hmotnost nemění), `supportsPickUp` = jde nést v rukou.
- **Model**: `blender/build_canister.py` (`blender.exe -b --python blenderuild_canister.py`, samostatná scéna, vlek se nepoužívá)
  vyexportuje `canisterFertilizer.i3d` / `canisterHerbicide.i3d`, štítky z `blender/canister_labels.py` (Pillow) do
  `objects/canister/textures/`, obrázky obchodu `store_canister*.dds` (512, nekomprimované). Tvar je shodný s `toolboxCanister`
  (`sdt_tanks.build_canister`), víčko tmavé, štítek s textem a u herbicidu s GHS piktogramem; barva těla přes `colorScale`
  (hnojivo `0,55 0,8 0,15`, herbicid `0,85 0,25 0,08`). Materiály `vehicleShader` s detailLibrary jako u vleku, bez vmask.
- Cena vychází z 25 % (hnojivo) a 10 % (herbicid) koncentrace: 20 l koncentrátu vyrobí 80 l, resp. 200 l postřiku (~1,2 €/l
  v herních datech), takže je koncentrát výrazně levnější než hotový produkt; cena je jen `<price>` v XML.

## Testování ve hře

- `tools/prepare_testsave.py` připraví slot 11: pickup s vlekem u pole 4 (1000l nádrž, 300 l tekutého hnojiva,
  s `--herbicide` herbicidu) a dvě běžící zakázky farmy 1: hnojení na poli 9 (bavlna, sprayLevel 0 → 1, v dosahu
  je jen roh pole) a herbicid na poli 8 (kukuřice, plevel 3 → 7). Vlastní pole v dosahu: 2, 3, 4, 5. Centrála má
  20 l nafty. Volby: `--drone none|S|M|L` (výchozí M), `--battery-count 0..5`, `--batteries 100,60,25` (nabití
  baterií v %, všechny ve slotech), `--drone-battery K` (baterie K v dronu), `--ibc 150` (IBC s přípravkem 3,5 m
  vpravo od vleku), `--diesel L`, `--time 22:00` (denní doba, výchozí 08:28), `--unfolded` (rozložený vlek),
  `--player-at-ladder` (hráč pěšky za žebříkem), `--player-at=x,z,yaw` (hráč pěšky jinde, např. `-665,212,270`
  na poli 4 čelem k řádkům), `--at=x,y,z,yaw` (souprava jinde: `-802.07,59.3,-252.70,-114` u čerpací stanice,
  **`-16.2,49.4,-153,90` s `--player-at=-17,-146.5,90` u dílny prodejce**, kde `R` pěšky otevře „Obchodník: úpravy
  vozidla“ a `Mezerník` Konfigurovat). Bez voleb vrací hráče na výchozí spawn.
- Obchod: `P`, `C` (hledat) „drone“, Enter; u vleku volby Baterie dronu a Dron (šipky vlevo u 0,027 / vpravo 0,19
  šířky okna, řádky 0,147 a 0,224 výšky).
- Ve hře se po vystoupení z vozidla někdy zrychlí čas na 360× (nejspíš jiný mod ve složce), noc pak rychle skončí;
  let a nabíjení běží v reálném čase vozidla, takže to měření nemění.
- `tools/fs25_input.ps1` umí kromě kláves i `mouseto`, `click` a `drag` (souřadnice 0..1 v klientské oblasti
  okna). Snímky berou jen klientskou oblast okna hry a přeskočí se, když okno hry není v popředí.
- Hru je potřeba pustit v okně, které se vejde na obrazovku (test běžel v 1600×900), jinak nesedí souřadnice
  kliknutí.
- Do vleku ze startu slotu 11: `Tab` 4× (Challenger, John Deere, MF, pickup), `X` rozloží vlek, `Tab` do vleku.
- Pole 2 je od vleku přes dvůr farmy se vzrostlými stromy a budovami: plánovač tam ukáže výšku přeletu 22–24 m
  „kvůli překážkám" a pojistka za letu se dá sledovat v logu s `DEBUG_FLIGHT = true`. S letovou plochou jako pás
  jižně od vleku podél horních okrajů polí 3 a 4 až do pole 2 (vlek ~4 m za jejím okrajem, v toleranci) je celý
  přelet v 8 m; když horní okraj plochy vede těsně kolem kůlny s kombajnem u vleku, zvedne se ten úsek na 17 m.
- Klávesa `BACKSPACE` je v `tools/fs25_input.ps1`. Kurzor u spodního okraje okna posouvá mapu plánovače (okrajový
  posun), pro snímky ho dávat nad panel (`mouseto:0.85,0.5`).
- Uložení ve hře: Esc → poslední ikona (Nastavení, `click:0.035,0.82`) → `Mezerník` (Uložit hru); pak `savegameBackup/savegame11_backup<čas>` drží
  stav před uložením, z něj jde slot 11 vrátit a znovu pustit `prepare_testsave.py`.
- `prepare_testsave.py --tractor pickup|jd3650|jd3650high|mt655|mt655high|mf8570|rtv` zapřáhne vlek za jiný vanilla stroj (oko a indexy spojek jsou v `TRACTORS`, polohy oček počítá `out/revize/T1/hitch_pos.py`; `high` = spojka typu `trailer` místo `trailerLow`), `--player-at-tractor` postaví hráče ke dveřím tahače (`E`, `Enter` nastartuje motor). `--diesel` se ořezává na 30 l. `fs25_input.ps1` umí `holdk:W+A,ms` (více kláves najednou). Při `Tab` mezi vozidly jde vlek z testovací soupravy hned za pickupem, Pavlův vlek ze slotu 5 stojí o dvě vozidla dál; `Esc` mimo plánovač otevírá nabídku, takže se zavírá plánovač tlačítkem Zavřít.
- Log hry: hlášky hry jsou v cp1250, české texty z `Logging.info` ale v UTF-8 (číst `grep -a` bez převodu).
- Z vleku se do pickupu přepne `Tab` 4× (Challenger, John Deere, MF, pickup); `Shift+Tab` otevírá Steam overlay.
- Zvuk: WASAPI loopback (`out/tmp/audio_venv` s `pyaudiowpatch`, `out/tmp/zvuk/loopback.py`) nahrál jen ticho –
  hra má `noFocus` hlasitost 0 a na výchozím výstupu (monitor BenQ přes HDMI) nic nehrálo; ověřuje se tedy logem.

## Známá omezení

- Plánovač zatím neumí ovládání gamepadem nad rámec vanilla kurzoru mapy (vyzkoušená je jen myš a klávesnice).
- Zakázka se vybírá jen celá; když pole leží v dosahu jen zčásti, dron udělá jen tu část a zbytek zakázky zůstane
  na hráči (plánovač na to upozorní).
- U zakázkového pole jdou statistiky postřiku vlastníkovi pozemku (NPC), stejně jako u vanilla postřikovače.
- Na zorané půdě není postřik hnojivem vidět jako změna textury; density mapa se mění (ošetřené řádky z trasy
  mizí, postup zakázky roste), stav pole ukazuje mapa.
- **Dráty elektrického vedení na Riverbend Springs nemají kolizi**, raycast je nevidí a dron jimi proletí.
  Ověřeno v datech mapy: `data/maps/mapUS/textures/powerLines.i3d` (vedení `powerLine01–11`) má skupinu
  `collision="false"` a tvary bez rigid body; kabely `cable` u sloupů v `textures/props/utilityPoles.i3d` také.
  Kolizi (`col`, skupina 0x3e = STATIC_OBJECT a další) mají jen sloupy, ty plánování i pojistka vidí. Ve 12 m
  přeletu tak dron vedení podletí nebo proletí; vyhnout se mu jde jen přeparkováním vlekem.
- Stromy mají kolizi jen na kmeni a větvích (listí ne), takže odstup se počítá od dřeva; boční odstup (výchozí 4 m)
  koruny většinou pokryje. Obejít překážku bokem uvnitř letové plochy plánování neumí (jen přeletí nad ní).
- Pojistka za letu hlídá jen vodorovný pohyb; svislé stoupání a klesání (vzlet, sestup na pole, přistání) ne.
  Kolizi se statickým objektem kolmo pod dronem při sestupu na pole to neřeší.
- Odhad času dávky vychází ve hře o 0–6 % delší než skutečnost (0.9), baterie proto s rezervou.
- Zbytek přípravku v dronu se při jiném typu ve vleku zahodí; ručně ho jde vrátit do vleku `Alt+1`. Při zmenšení
  nádrže nebo odebrání dronu v dílně se náplň dronu ztratí.
- Přepočet trasy (každých 5 s a po změně nastavení) trvá na poli 4 2–8 ms, na poli 2 s L při změně bočního odstupu
  60–133 ms (krátké zadrhnutí při klikání v plánovači); běžný přepočet za letu se nepočítá znovu (paměť).
- Multiplayer není ve hře vyzkoušený (ani event letové plochy).
- Letová plocha: samoprotínající se mnohoúhelník se nekontroluje (vnitřek se bere pravidlem sudý–lichý). Plocha
  hlídá jen vodorovnou cestu, výšku dál určují raycasty v pásu ±2,4 m kolem osy úseku; když ji uživatel nakreslí
  těsně podél budovy, úsek se zvedne. Plocha se vztahuje k poli, ne k místu vleku: po přeparkování vleku mimo ni
  plánovač hlásí „Vlek stojí mimo letovou plochu", dokud se neupraví. Přesuny mezi řádky v dávce plochu
  nerespektují (letí nad polem přímo, i přes zářez nekonvexního pole). Rozkreslená (neuzavřená) plocha se
  neukládá a jiní hráči ji nevidí.
- `Alt+0`: vanilla `0` je Zatroubit; jestli při `Alt+0` troubí i vlek, se ve hře ověřit nedalo (zvuk se nesnímá).
- Zvuk rotorů je ověřený jen logem (vzorek se načte bez chyby, hraje, výška a hlasitost jdou s otáčkami), ne
  poslechem. Zdrojová nahrávka je malý dron (Mavic Mini) snížený o čtvrtinu; velký T50 zní hlubším „dunivým“ tónem.
  Jeden vzorek pro všechny rotory, žádný zvlášť zvuk startu, postřiku ani změny zátěže při stoupání.
- Mlha postřiku je vlastní částicový efekt z kouřového atlasu: nemá vlastní texturu kapek a nereaguje na vítr.
  Ve hře ověřená jen v ladicí smyčce (vznášení tam a zpět), ne za skutečné mise.
- Baterie: odběr při vznášení se pozná jen podle vodorovné rychlosti pod 2 m/s, vítr ani náklon se nepočítají.
  Nabíjení je lineární až do 100 % (skutečná nabíječka nad 95 % zpomaluje), baterie v dronu se na plošině nenabíjí,
  opotřebení baterií (cykly) se nepočítá. Nabíjení i let jdou v reálném čase vozidla: zrychlení času hry je nezrychlí.
- Nabíjení z vanilla nabíjecí stanice pro elektromobily není (sekce Elektrocentrála).
- Úchyty dronu jsou jen vizuál; dron drží na vleku to, že je součástí modelu. Převrácení vleku ve hře nezkoušeno.
- Dosah z baterie vychází u všech variant nad strop varianty (S 600 / M 900 / L 1200 m, rozhodnuto 2026-10-05), takže
  se kruh s výškou přeletu nemění; menší dron má menší dolet, ale baterie na jeho okraji není vyčerpaná.
- Obrázek vleku v obchodě a ikonu kreslí export (Workbench, headless) při každém exportu; vzhled se kontroluje v obchodě.
- Dílna po změně konfigurace vytvoří vlek znovu, odpojený od tahače (vanilla).
- Plánovač u vleku bez dronu se otevře (`Alt+7`, displej), ale start hlásí „Na plošině není dron“; tablet ho mezi cíli nemá.
- Odhad plánovače simuluje nabíječku po 5s krocích a předpokládá, že vlek zůstane rozložený a mise nepřerušená.

## Stav

- [x] Revize 2026-10-05, test ve hře T1 (Middle, M/S/L): dolet S 600 / M 900 / L 1200 m v kruhu plánovače, plnění dronu 1,0 / 1,5 / 2,5 l/s a přečerpání do IBC 20 l/s (změřeno), postřik 58 l/ha, mlha postřiku se vykresluje (viz níže), konec mise jako ingame notifikace i v pickupu, nový status „centrála vypnutá“ (hláška + plánovač), 0 baterií (hláška, plánovač), uložení a načtení uprostřed mise (dron v letu, baterie ve slotech, krytí pole), žádné „SDT DEBUG“ v logu, Middle za pickup, John Deere 3650, Challenger MT655, MF 8570 (třetí spojka) a Kubota RTV X1140 (zapřažení, jízda 40 km/h, couvání, brzdění). Nové zvuky se ověřují jen logem (bez chyb), ne poslechem. Rozložený zapřažený vlek je kinematický a tahač s ním nejede (po složení `X` jede); odpojit rozložený nejde, hláška „Nejdřív vlek slož“ se zobrazí.
- [x] Revize 2026-10-05, test ve hře T2 (Mini, dron S, 3 baterie): načtení bez `Error`/`attempt to`/`Index not found`/`Particle System`; zapřažení s ojí 1,85 m za pickup, Challenger MT655, JD 3650 (`trailerLow` i `trailer`), MF 8570 (třetí spojka) a Kubotu RTV, jízda a couvání (plný rejd za MT655 bez viditelného zasahování do kola); rozložení a složení desky (víko šachty, úchyty, vyjetí, překlopení, sjetí dronu, nožičky), dron dosedá mezi závěsy, hadice na desce, koncovka v držáku; blokace rozložení překážkou pod deskou (hláška) a obrys desky (zelený / červený); let S z desky, postřik (mlha), přistání, míchání voda + koncentrát (5 %), výměna baterie, noc 22:00; kanystry z bedny vznikají za vlekem vpravo, mimo vlek i desku; přečerpání do IBC; obchod (3 900 €, obrázek, konfigurace), dílna (Baterie 3, Dron Malý, vrtule, proužky); uložení a načtení uprostřed mise (deska zůstala rozložená). `SprayDronePad.drawPreview` teď barví obrys červeně i při překážce / krátké hadici (dřív jen při svahu), kontrola 4× za sekundu. `prepare_testsave.py`: oko Mini (`MINI_HITCH_OFFSET` 4,45 + 2,758), `--ibc-behind M`, hráč u Mini `--player-at-ladder` 3 m za vlekem.
- [x] Revize 2026-10-05, test ve hře T3 (Max, dva drony S/M/L): načtení bez `Error`/`attempt to`/`Index not found`/`Particle System`/`Missing l10n` (jen cs, přepnutí jazyka přes `game.xml` nezabralo); zapřažení za JD 3650 (`trailer`), MF 8570 a MT655 (jízda, rejd, couvání; z 35 km/h do stání za ~1,6 s bez zadrhnutí), vlek 2 x 3000 l složený i rozložený, truhla nabíječky s otevřeným víkem, dvě hadice a dva rozložené drony viditelné; plánovač „Drony v misi“ 1/2 (1 dron = 2 dávky/5,0 min, 2 drony = 3 dávky/3,6 min), let obou dronů, `Alt+9` pohled z dronu 1/2 a zpět, uložení uprostřed mise s `drone2` v savegame, noční LED, ingame notifikace „1: Dron: pole je hotové“ i když sedíš v tahači. Neověřeno vizuálně (snímky nečitelné): vyjmutí 16+ kanystrů z bedny, mlha z boku, brzdění vzhledem k oji. Pickup: savegame vlek zapřáhl násilně (typ spojky se nekontroluje), XML spojek (`trailerCar`/`semitrailerCar` vs `trailer`/`trailerLow`) říká, že ručně nejde. `prepare_testsave.py`: u Maxu `trailer` -> `inputJointIndex` 1, `trailerLow` -> 2; nové volby `--canisters N`, `--canisters-same`, `--diesel-canisters N`.
- [x] Revize 2026-10-05, test ve hře T4a (Max, balíky h + i; Middle zběžně): načtení bez `Error`/`attempt to`/`Particle System`/`Index not found`; zapřažení za JD 3650 přes `trailerLow` (inputJointIndex 2), MF 8570 a MT655, jízda; pickup: savegame vlek zapřáhne násilně, po odpojení (Q) se na správném místě znovu nepřipojí (typ `trailerCar` není v Maxu). Hláška „Vlek je rozložený a drží na místě…“ u Maxu i Caru se zobrazí po plynu a opakuje po ~4 s, po složení (`X`) nepřijde a tahač jede. Barva mlhy: hnojivo žlutozelená, herbicid bílomodrá, mlha z obou dronů, v logu nic. Ukazatel naplnění: u Maxu s dvěma drony byl jeden řádek oříznutý („Nádrže dronů 33 · 37 l (v dr…“) a s prázdnými dronem se sloučil s hlavní nádrží téhož přípravku (vanilla ukazatel slučuje řádky bez dovětku), opraveno: titulek „Nádrže dronů“ + dovětek „(17 · 17 l)“, celkem 5 řádků (`getFillLevelInformation`, překlad `sdt_fill_droneTanks`); Middle „Nádrž dronu (v dronu)“. Souběžné plnění obou dronů: průtok M 1,5 l/s se dělí (0,75 l/s na dron, jedno čerpadlo, jak je popsáno u Servisu). Bedna Max: vyjmutí 24 kanystrů najednou přes dialog (R, Enter) vyrobilo ve světě 24 objektů (savegame, mřížka 6 × 3 a druhá vrstva 6 ks, 7 m za osou vleku, polohu vůči zádi vleku jsem nepřeměřil), víko se otevírá klikem; štítky „NÁDRŽ 3000 L / VÝTOK“ čitelné; plánovač 1 dron = 1 dávka/2,5 min vs 2 drony; let jedním dronem, `Tab` za letu na jiné vozidlo a prodej vleku v dílně za letu bez chyby a úniku v logu. Obchod Max: 48 000 € základ, Malý +14 000, Střední +24 000, Velký +44 000, obrázek 2 × 3000 l; obrázek Middle ukazuje 1000 l. `Alt+7` jde jen ze sedadla vleku (záměr, kdykoli ve vleku); z tahače se neotevře a `Esc` pak otevře nabídku. Jazyk en nešel ověřit: Steam verze bere jazyk ze Steamu (`getIsLanguageDisabled`), `game.xml#language` hra ignoruje (log `Language: cz`); cz × en klíčů 223 : 223.
- [x] Revize 2026-10-05, test ve hře T4b (Middle, Mini, bedna na kanystry; bez změn kódu a modelu): bedna Middle (šest svislých žeber na čele i zádech, víko na pantech vpředu, tři západky vzadu, nápisy KONCENTRÁTY / kanystry 20 l a SERVIS / NÁŘADÍ čitelné z místa u západek, výstražný trojúhelník) zavřená i otevřená ze čtyř stran bez šuplíkového vzhledu; zbývají jen boční madla na krátkých stěnách (nosná, vypadají jako šuplíkové držadlo, jen ke zvážení). Mini bedna (madlo a dvě západky na dlouhé stěně, oranžový pruh na víku) a štítek 450 L (výtlačná trubka ho nezakrývá). Štítky NÁDRŽ 1000 L, VÝTOK, koncentrát, mixér čitelné a nezrcadlené, bez viditelného z-fightingu při pohybu kamery. Dílna Middle (R + Mezerník): 5000 l + dron L = 29 000 €, bez chyby v logu. Mini: rozložení na rovině (nožičky stejné, deska vodorovná), na prudkém svahu (kolem -736, 811) hláška „Terén je pro přistávací desku příliš svažitý“ (mírný svah 7° vizuálně neověřen), `padHose` (dočasně HOSE_ARC 3,2 → hláška „Hadice k dronu na desce nedosáhla“, kód vrácen), pohled na desku s hadicí, jízda s pickupem a JD 3650 včetně brzdění z ~50 km/h bez zadrhnutí a opěrné kolečko nahoře. Lety: Middle S i L (vzlet, mlha, přistání, doplnění, výměna baterie, mixér voda + koncentrát 5 %: 19 l vody a 1 l koncentrátu na dávku), Mini S (plnění hadicí na desce, přistání na H). Stojan nafty Middle: kanystr nafty se vsaje s notifikací a víko bedny zůstane zavřené; cizí 25 l a prázdný kanystr se podle kódu nevsají (nezkoušeno ve hře, bez cizího modu). Neověřeno: noc s rozsvícenými světly tahače (L v testu světlo nezapnulo), Max stojan nafty, blikání kontrolek nabíječky.
- [x] Revize 2026-10-05, test ve hře T5 (závěrečný běh po druhém kole: Lua R2-L, balíček R2-P, modely R2-M1/M2/M3; snímky `out/revize/T5/`): Middle, Mini i Max se načtou bez `Error`/`attempt to`/`CPU-Mesh`/`raw format`/`#prefix`/`Missing l10n`/`SDT DEBUG` (jediný Error v logu je cizí mod FS25_ZetorX340); obchod: tři vleky v kategorii Rozprašovače (6 100 / 3 900 / 48 000 €), kanystry (hledání „kanystr“) se správnými DXT ikonami, mod verze 1.0.0.0. Middle: `Alt+7` u složeného vleku jen hláška „Plánovač jde otevřít jen u rozloženého vleku“; F1 ukazuje `Alt+5`; žebřík funguje i po cyklu rozlož → slož → rozlož (hráč vylezl na palubu), madla trčí ~1 m nad palubu jen u rozloženého vleku, složený je má sklopené; bedna bez bočních madel, kanystry v bedně i vyndané mají štítek v barvě atlasu (zelené hnojivo / oranžový herbicid, tělo přebarvené, štítek ne), listy dronu M tmavé v obou polohách. **Opraveno:** vanilla „složit vše“ (`Ctrl+X`, `FOLD_ALL_IMPLEMENTS`) registruje sám vlek, takže ho `getIsFoldAllowed` nerozeznal od vlastního `X` a dron se odvolal; teď `Foldable.actionEventFoldAll` nastavuje `SprayDroneStation.foldAllActive` a za letu přijde jen hláška `sdt_warning_droneFlyingFoldAll` (dron letí dál, ověřeno F1 stavem „LETÍ DÁVKU“), `X` na vybraném vleku z pickupu nebo ve vleku dron odvolá („VRACÍ SE“). Mini: bedna se svislými žebry a pochozím víkem, deska s heliportem H (dron S na něm přistál), pruhy, let S. Max: nápis „8 × 52 V“ na boku, navíječe v kapsách paluby a hadice přes hranu kapsy k oběma dronům při souběžném plnění, pevná madla žebříku, plánovač bez blikání (dva snímky po 1,2 s shodné), let obou dronů, `Alt+1` vybere dron s větší náplní (20·20 → dron 1; 0·18 → dron 2) a po vyprázdnění se zastaví. Neověřeno: rozjetí vleku za letu (vlek je kinematický, kód `STATUS_TRAILER_MOVED` jen přečten), noc – dron na plošině LED nesvítí (záměr) a světla vleku při `F` v pickupu nebyly na snímku vidět, Max bedna zblízka jen zdálky (bez madel).
- [x] Mlha postřiku: `ParticleEffect` bere z uzlu jen tvar emitoru a systém částic ze šablony podle `particleType`, takže vlastní `Dynamic` ze `sprayMist.i3d` nikdy nešel použít (log `Particle System emitter mesh for shape 'mistM' could not be loaded`, mlha se nevykreslovala). `SprayDroneStation.loadSprayMist` teď načte `Dynamic` přímo (`ParticleUtil.loadParticleSystemFromNode`) a mlha je vidět; barva se podle přípravku už nemění (jedna bílá mlha). Foldable má `objectText` „vlek“, takže se akce jmenuje „Složit: vlek“ místo „Složit: …“ podle typeDesc.

- [x] Vlek: nádrž 1000 l (od 2026-09-30, dřív 600 l; indukční nádrž jen vzhledová, ~50 l místo 100 l) na `liquidFertilizer` a `herbicide`, skládací žebřík, nastoupení jen rozloženého
      (`scripts/SprayDroneStation.lua`), dron jako součást modelu (`<prefix>Root`)
- [x] Kruh dosahu ve světě, výpočet trasy a dávek, HUD a nápověda F1
- [x] Plánovač letu: mapa, vlek, kruh dosahu, obrysy polí s důvodem, výběr klikem, trasa po dávkách, souhrn,
      Spustit let / Návrat domů / Zavřít, posun a zoom mapy (ověřeno ve hře)
- [x] Let, postřik (tekuté hnojivo i herbicid), přistání, doplnění z vleku, výměna baterie, návrat, blokace složení
- [x] Zakázky: výběr pole hnojicí i herbicidové zakázky, odmítnutí zakázky na jiný přípravek, postup zakázky roste
      (hnojení 0 → 2–3 %, herbicid 0 → 6 % po prvních dávkách, ověřeno ve hře)
- [x] Ukládání a pokračování mise po načtení
- [x] 0.4.0.0: dron na plošině uprostřed a po směru jízdy; rozložení ramen a listů před vzletem, složení po misi;
      točení vrtulí s roztočením, doběhem a dotočením do klidu; plynulá rychlost, yaw a náklon; odhady času;
      výška přeletu nad překážkami, limit 60 m, pojistka za letu (vše ověřeno ve hře na poli 2, singleplayer)
- [x] 0.5.0.0: letová plocha v plánovači (kreslení, uzavření, smazání bodu i plochy), cesta plochou (graf
      viditelnosti + Dijkstra), přelet nízko (`corridorHeight` 8 m) s kontrolou překážek, hlášky a blokace startu,
      když cesta není, délka a čas přeletu v souhrnu, přelety v mapě a ve 3D, uložení a načtení (ověřeno ve hře na
      poli 2, singleplayer); návrat domů na `Alt+0`
- [x] 0.6.0.0: dron se rozkládá a skládá s vlekem (i po načtení savegame), před vzletem jen roztočí vrtule, složení
      vleku blokují dobíhající vrtule; zvuk rotorů (CC0) s výškou a hlasitostí podle otáček; baterie 8 min s plnou
      nádrží, odběr podle hmotnosti náplně a fáze letu, výměna až pod 30 %, plánovač počítá dávky se spotřebou
      a výměnami; efekt postřiku z vanilla sítě Hardi Mega s materiálem podle přípravku (ověřeno ve hře na polích
      4, 9 a 2, singleplayer; zvuk jen logem, herbicidová barva efektu nevyzkoušená)
- [x] 0.7.0.0: elektrocentrála (nafta 30 l, tankování na čerpací stanici), 2 náhradní baterie s nabíjením (10 min
      30 → 95 %, 2,2 l/h jen při nabíjení, i u složeného vleku, vypínání `Alt+6`), výměna za nejnabitější a čekání na
      nabití, plánovač se servisem, čekáním a naftou; plnění dronu čerpadlem 60 l/min; LED ramen (přední červené,
      zadní zelené blikají 1 Hz) se světly; kolize žebříku; úchyty lyžin dronu ve skládací animaci; nádrž a baterie
      v ukazateli naplnění; přepínání čar ve světě `Alt+5`. Ověřeno ve hře (singleplayer): hráč se o žebřík zastaví,
      tankování 2 → 30 l, nabíjení 6,5 %/min a 0,0061 l za 10 s, čekání na nabití a výměna při 95 %, plnění, světla
      v noci za letu a zhasnutá na plošině, uložení a načtení baterií a nafty, zapnutí/vypnutí centrály, nabíjení
      složeného vleku bez nikoho uvnitř, úchyty otevřené/zavřené, čáry skryté/zobrazené. Neověřeno: zvuk a kouř
      centrály (kouř za šera nebylo vidět, zvuk se nesnímá), mise bez nafty až do konce (`STATUS_NO_FUEL`).
- [x] 0.8.0.0: opěrné kolečko s kolizí; plynulé rozkládání dronu; ukazatele (nahoře dron, dole vlek s řádkem
      nabíječky); baterie jako model ve slotech (držák u centrály / nabíječka na palubě / dron), výměna za první plnou,
      nabíjení všech najednou s naftou úměrnou počtu; úchyty mizí; bodová světla LED jen nad 2 m; efekt jako kužely
      pod tryskami; zaoblené rohy, přílet po směru řádku, půlkruhové přejezdy, výškový profil; nastavení letu
      v plánovači; pás překážek podle poloměru dronu a bočního odstupu, překážky v mapě; dosah z baterie (strop
      1500 m); přečerpání dron → vlek (`Alt+1`) a vlek → IBC (`Alt+2`); heliport; nabíječka s kabelem; hadice z článků
      (namotaná / ležící / prověšená). **Ověřeno ve hře (2026-09-28, singleplayer)**: vlek po odpojení stojí na kolečku,
      skládání i rozkládání plynulé, pořadí ukazatelů, baterie přeskakují mezi sloty (log i model), nabíjení 2–4 ks
      najednou, IBC 300 → 265 l, dron → vlek 40 l, bodová světla v noci, kužely postřiku, hadice k hrdlu M a S,
      heliport, nabíječka, dosah 1500 m, nastavení (klik, kolečko, Q/E, uložení), překážky na poli 2 (4 m vs 15 m),
      odhad dávky proti letu, uložení a načtení s pokračováním mise. Neověřeno: detail oblouků ve 3D (jen log a mapa),
      pojistka při bočním odstupu 1 m, herbicid po vyprázdnění vleku, hadice u L zblízka, 0 baterií ve hře.
- [x] 0.9.0.0: varianty dronu S / M / L a bez dronu jako konfigurace v obchodě a dílně, baterie 0–5 za 1 500 €,
      modely a baterie tří velikostí, parametry, zvuk a efekt podle varianty. **Ověřeno ve hře**: obchod (volby,
      ceny, náhled se mění), dílna M/3 → S/2 (10 000 €) a S/2 → L/5 (29 500 €) s přenesením nabití (100/60 % zůstalo,
      nové plné), let a postřik všech tří variant, vlek bez dronu (prázdný heliport, bez úchytů, F1, `Alt+7` hláška,
      nabíjení, IBC), L s 5 bateriemi v noci na poli 2 a uložení/načtení. Neověřeno: 0 baterií (hru zavřel někdo jiný,
      ověřeno jen offline testem), zvuk poslechem, MP.
- [ ] Úpravy 2026-10-11 (všechny tři vleky; ověřeno jen Blender kontrolami, offline Lua testy a `tools/check_all.py`, **ve hře ne**; co zkusit, je v `docs/PLAN-uprava-2026-10-11.md`, sekce „Stav“):
      Mini (podvozek z Utili Trailer 2, kola a blatníky vně rámu, šířka 2,60 m, výtlak čerpadla nízko při palubě, boční plechové stěny, víc polepů, nízká nádrž 300 l,
      navíječ s osou podél vleku), Middle (kratší vůz, větší nálepky na zadní stěně skříně, sklopný žebřík u pravého předního rohu, nohy), Max (oj podle DPW 1800, oválné nádrže,
      druhý navíječ vedle nabíječky, žebřík, nohy), rolety skříně na kanystry (vyjedou nahoru do pouzdra), bedny se nezavírají samy (zůstává i po odchodu hráče), voda jen u hladiny (`waterTrailer`), Ctrl+I vypouští
      koncentrát, zvuky (roleta, víka, lití, plnění, skládání), výběr pneu (nové `saveId`).
- [ ] Úpravy 2026-10-13 (všechny tři vleky; Blender kontroly, `tools/check_all.py --no-build` a offline Lua testy, **ve hře ne**): vrtule drona složené symetricky kolem motoru (`build_drone.py`),
      jedna silniční pneu bez výběru a vlastní disky (`sdt_rims.py`, `export_rims.py`; Max Hybrid HD3 + `sdtRim22`, Mini/Middle Lizard Destination Farm 280/70 R15 + `sdtRim15`),
      kolize sloupků a blatníků/krytů kol (`colPost*`, `colFender*`, `colWheelCover*`), zvuky po krocích místo smyčky skládání (`droneUnfoldStep`, žebřík, Mini pad), Max: oj s detaily,
      volba spojky za traktor / za auto, vzduch + elektrika (`connectionHoses`), víka kapes navíječů; nožky: `levelTolerance` 2,5° a `maxTilt` 15°; Mini rozložené v obchodě.
      Víko bedny se po odchodu hráče nezavírá (jak je od 2026-10-11). Pneumatické nožky jsou jen návrh: `docs/PLAN-nozky-vzduch.md`.
- [ ] Druhé kolo oprav 2026-10-13 (Pavel po hře; Blender BVH kontroly a offline Lua testy, ve hře ověřena jen oprava kolizí):
      **Kolize** - skutečná příčina: při přepnutí dynamického vleku na kinematický (`SprayDroneStation.updateFreeze`, rozložený vlek) engine odsune všechny dětské
      kolizní tvary o těžiště nahoru, takže hráč prochází nádržemi a propadá palubou (změřeno `colMap`, `colProbe`). Tvary ve skupině `collisions` se po dobu zmrazení
      posouvají o těžiště zpět; kořenový tvar komponenty je proto jen drobná krychle a rám vleku je dětský tvar `colChassis`; Mini má kolize panelů bedny (`colPad*`, na čepech).
      Vlek načtený už rozložený (kinematický od začátku) se neposouvá. **Zvuky**: vrzání při skládání dronu a u žebříku pryč, dron cvakne jednou (`UNFOLD_STAGES = {0.98}`), posun dronu na Mini
      beze zvuku. **Kola**: blatníky (Mini) a kryty kol (Middle) mají střed oblouku v ose kola ve hře (`WHEEL_R + TIRE_Y_OFFSET`), vůle 4 cm nad skutečnou pneu (0,39 m), zdvih odpružení 0,05 m,
      plechy bez splývajících ploch (to blikalo); barva ráfků v obchodě (`rimColorConfigurations`, materiál `rim_outer_mat`). **Mini**: baterie v obchodě nelétá (`startBatteryMove` mimo
      `SHOP_CONFIG`), barva bedny (`baseColorConfigurations`, materiál `SDT_CrateGreen`) a nálepky (`designConfigurations`: kompletní / jen logo / bez), po změně těchto voleb se bedna v obchodě
      složí (`SprayDronePad.openInShop`), po jiné změně zase rozloží; konec hadice (kov) nezasahuje do hadice (`sdt_nozzle.INLET_LEN`, koncovka v klidu o 8 cm dál). **Middle a Max**: pryč knoflíky
      s červenou rukojetí nad nohama; nohy se vysouvají 5 s a vlek se vyrovnává 2 s (animace `foldLadder` má 10 s, vše ostatní zůstalo v prvních 3 s; zlomky `trailerFoldEnd` 0,2,
      `securedFoldTime` 0,24, `batteryStowFrom/Until` 0,018 / 0,165, nohy 0,99 -> 0,5 -> 0,3). **Vrtule**: složené listy leží na jedné přímce přes střed rotoru (podél ramene, spodní přední listy
      o 15 stupňů, S dron o 45 stupňů - `SPECS[...]["blade_fold"]`), rozložené jsou napříč ramene přes střed; dřív byly složené listy vedle sebe, nebo přes sebe.
- [ ] Zakázka dokončená dronem celá (nevyzkoušeno, trvá desítky minut; výpočet postupu je vanilla)
- [ ] Multiplayer ve hře (kód napsaný, neověřený)

## Na příště

0. Nafta jako koncentrát (2026-10-11, ověřeno jen testem logiky `tmp/test_toolbox_parts.py`, `tools/lua_check.py` a Workbench renderem, **ve hře ne**): u Mini, Middle i Max vsátí naftového
   kanystru jen po otevření víka / vrat a nad otvorem bedny, nafta ve slotu (každém) i v dialogu „Nafta – kanystr“, výdej za vlek, ruční lití nafty do elektrocentrály a koncentrátu do
   indukční nádrže dál funguje (R i naklopení), uložení a načtení slotu s naftou, multiplayer (stav slotů). U Middle a Max po posunu `toolboxActivateNode` do poloviny výšky vrat
   (dřív o 0,36 / 0,5 m výš) a `intakeBelow/Above` 0,7: kanystr v ruce u otevřených vrat se vsaje ve všech patrech (hráč stojí na zemi, vrata Max začínají 1,0 m nad zemí),
   dialog (R) a klik na vrata jdou ze vzdálenosti `activateDistance`, cizí 25l naftový kanystr se nevsaje.

1. Ve hře ověřit vlek s 0 bateriemi (`prepare_testsave.py --battery-count 0 --unfolded`: `Alt+8` a Spustit let →
   „Dron nemá baterii, nemůže vzlétnout“, v plánovači červeně pod řádkem dronu).
2. ~~Obrázek do obchodu a ikona~~ — export je kreslí sám při každém běhu (`export_*_mod.py`), jen vizuálně zkontrolovat v obchodě.
3. ~~Rozhodnout strop dosahu~~ — rozhodnuto 2026-10-05: S 600 / M 900 / L 1200 m (`maxRange` v blocích `<drone>`); z baterie vychází 2,6–3,6 km, platí vždy strop varianty.
4. Dílna účtuje plnou cenu nově zvolených voleb (vanilla), ne rozdíl; kdyby vadilo, řešit vlastním výpočtem ceny.
5. Zadrhnutí 60–130 ms při změně bočního odstupu v plánovači na poli 2 (přepočet všech dávek po každém kliku) —
   přepočítat až po krátké prodlevě.
6. Neudělané z 0.8: obejití překážky bokem uvnitř letové plochy, pojistka při svislém stoupání a klesání.
7. Ve hře ověřit zkrácený panel nápovědy (skryté akce `Alt+1/2/5` dál fungují); bedna už žádné klávesy nemá (sání + aktivace + dialog).
8. Mini ve hře: dvě bedny s vlastním víkem (obě se odklápí k nádrži, žádný průnik s nádrží), klik a `R` u každé bedny otevře / ukáže jen její sloty
   (pravá 1-4, levá 5-8), vsátí kanystru jen do otevřené bedny, nad kterou byl, výdej kanystrů z té bedny na její straně, vypuštění nádrže z dialogu
   levé bedny do jejích volných slotů, multiplayer (stav víka obou beden, příkazy s číslem bedny, notifikace vsátí), nafta ve slotu libovolné bedny
   (od 2026-10-11 se naftový kanystr vsává stejně jako koncentrát: jen nad otevřenou bednou, bez zvláštního otvoru), Middle a Max s naftou.
   Mini po úpravě 2026-10-11: rozložení a složení bedny (boční stěny se vyklopí ven a sklopí k zemi vedle vleku podle terénu, pak se panely sklápějí a dron se nesmí hýbat, než je plošina
   rozložená; nožičky se ukážou až při dorozložení panelů; po rozložení se dron otočí hrdlem k navíječi a dosedne na H, při složení opačně a boční stěny se na konci zvednou na lem paluby),
   dron v rovině plošiny na svahu, víko šachty ve složeném i rozloženém stavu, kola a blatníky vně rámu a chování za tahačem (náprava y -0,45, pružiny), hadice z navíječe s osou podél vleku
   (plynulý výstup, dosah k dronu, žádný průnik, výřez v přední stěně bedny, koncovka do hrdla), nádrž 300 l (plnění, popisek na horní ploše, výtlak čerpadla nízko při palubě), kanystry
   v obou bednách (uzly 1-4 vpravo, 5-8 vlevo), `SDT_CONCENTRATE_*` (načtení `xml/fillTypes.xml`, kanystr -> bedna -> koncentrát ->
   míchání -> dron s `herbicide`), orientace dronu po načtení uložené hry s rozloženým vlekem (`homeYaw` s otočeným carrierem). Stará uložená hra nese
   konfiguraci `TANK450`; vlek je potřeba v dílně / obchodě obnovit (zpětná kompatibilita se neřeší).


## Úpravy 2026-09-29 (osm bodů od Pavla)

- **Hadice mimo dron**: plnicí hrdlo je na straně hadice (vpravo, `DRONE_FILL_PORT` -X) vedle radaru a `hoseVia` vede
  nad přední hranou trupu na téže straně, takže hadice nepřechází přes radar ani ramena. Ve hře jen zběžně ověřeno.
- **Pole od začátku**: dron si pamatuje, kde už postříkal, vlastní pamětí (`spec.coverage`, `SprayDroneRoute.markCovered`):
  pro pole a druh postřiku intervaly po řádcích (číslo pruhu × šířka záběru, souřadnice podél řádku) a po úvratích
  (`headlands[i]`, viz **Úvratě**). Trasa se z ní
  skládá jen z neobletěných míst, do hustotních map pole (úroveň hnojení, plevel) se nedívá, takže ruční hnojení ani
  postřik jinou technikou dronu práci nezakazují. Po dokončení pole (`STATUS_FIELD_DONE`) se paměť smaže a další mise
  letí pole znovu; tlačítko *Pole od začátku* (Mezerník, `RESET_FIELD`, jen server, bez běžící mise) ji smaže ručně.
  Pole se nemění. Paměť se ukládá (`#coverage`) a synchronizuje klientům vlastním dirty flagem. Změna druhu postřiku, záběru
  nebo počtu úvratí (`hl`) paměť pole zneplatní. Ve hře neověřeno po přepisu.
- **Kontrolky nabíječky**: `Charger_Led_<šachta>_<0..3>` (mapované uzly) řídí `SprayDroneStation.updateChargerLeds`: svítí jen šachta
  s dosedlou baterií, počet čárek = nabití ve čtvrtinách (aspoň jedna), nejvyšší čárka bliká, dokud se baterie nabíjí
  (`generatorRunning`). Prázdná šachta nesvítí.
- **Bez popruhů**: z hlavní nádrže zmizely černé pásy (`leg_tank`).
- **Složit / rozložit z vleku**: `foldingParts#requiresPower="false"`, ve vleku jde X bez motoru, vlek je vždy
  nastupitelný (i složený) a `getIsFoldAllowed` už neblokuje složení zevnitř. Ověřeno ve hře.
- **Rozložený vlek stojí**: `attachingMinLimit` / `detachingMinLimit` 0,98 (nejde připojit ani odpojit, hláška
  `sdt_warning_foldFirst`) a `updateFreeze` dá komponentu do kinematické fyziky, dokud animace skládání < 0,98. Připojení a
  odpojení i jízda s autem ve hře neověřeny (motor auta se skriptem nastartovat nedal).
- **Vrtule v obchodě**: konfigurace *Vrtule dronu* (Podle modelu, černé, bílé, karbonové, fosforeskující zelená, žlutá,
  oranžová) a *Proužky na vrtulích* (podle modelu, bez, oranžové, žluté, červené, zelené, modré, bílé). List má materiál
  `Prop_Blade` (barva přes `colorScale`, karbon přes `setMaterial` z ramene `<prefix>Arm_1`) a dítě `<list>_Tip` se dvěma
  pruhy (`Prop_Tip`); uzly v `<propBlade>` / `<propSource>`. Výchozí vzhled: T50 bílé bez proužků, T25 a T100 karbon
  s oranžovými. V obchodě a s fosforeskujícím nástřikem neověřeno.
- **Hadice kulatější**: 24 stran místo 10–12, 48 článků místo 24 (`fillHoseSeg1..48`), plynulejší pevné úseky.


## Ladění za běhu (DEBUG)

`scripts/SprayDroneDebug.lua` (vypnutí celého: `SprayDroneDebug.ENABLED = false`) čte jednou za sekundu soubor
`Documents\My Games\FarmingSimulator2025\modSettings\FS25_SprayDroneTrailer\debug.xml`; bez něj je vše vypnuté. Zapisuje ho
`tools\sdt_debug.ps1`, například `.\tools\sdt_debug.ps1 -InfiniteBattery -InfiniteTank -Speed 4`, `-MistLoop` (testovací let
vedle vleku bez vzletu, mlha stále zapnutá), `-Command coverField|resetCoverage|chargeAll|fillTrailer|fillWater|fillConcentrate|fillDiesel`, `-Off`.
Zásahy do hlavního kódu jsou označené komentářem `-- DEBUG` (násobek dt v `onUpdate`, `drainBattery`, `flushSpray`,
`debugMistLoop`, `updateSprayEffects`). Jen server / hostitel.

- **Velikost nádrže vleku (obchod, 2026-09-30, upraveno 2026-10-04)**: vanilla konfigurace fillUnit 800 / 1000 (výchozí) / 1500 / 3000 / 5000 l (saveId TANK800…TANK5000, ceny 0 / 400 / 1300 / 3500 / 6000 při základní ceně 6100). Nádrž 300 l odebrána (základní cena +500, ceny konfigurací −500, takže 800 / 1000 / 1500 stojí stejně jako dřív). 800 / 1000 / 1500 l jsou válcové nádrže, 3000 a 5000 l hranaté PE nádrže (`BoxTank` v `sdt_bigtank.py`, rozměry `BOX_GEOM` v `decal_layout.py`): kulatá nádrž takového objemu se pod horní plošinu a před zadní bednu nevejde. 3000 l (1,76 × 1,26 × 1,40 m) odpovídá objemu, 5000 l (1,84 × 1,34 × 1,62 m) vyplňuje všechno volné místo a geometricky má ~4000 l (zadní stěna y 1,32, bedna začíná na 1,51). Staré uložené id `1` hra nenajde a použije výchozí (Info v logu).


## Nápady do budoucna (zapsáno 2026-09-30, zatím neřešit)

- **Druhý vlek pro dva drony** (dva drony současně / střídavě z jednoho vleku).
- **Dron-opakovač (repeater)**: dron, který se pošle na místo a rozšíří dosah signálu (dnes strop dosahu `maxRange` / 1500 m od vleku).
  Nejdřív ověřit, jak to funguje v reálu (DJI opakovač / relé pro Agras – rozšíření dosahu ovládání, omezení zorného spojení,
  výdrž baterie opakovače), teprve pak navrhnout herní model.

- **Plánovač: koridor a ikony (2026-09-30)**: koridor přeletu je jedna plocha, konvexní obálka všech přeletů rozšířená o poloměr dronu a boční odstup (SprayDronePlannerScreen:getCorridorHull, cache podle routeInfo.transits). Vlek je malá černobílá ikona bez popisu (gui/icons/mapTrailer.dds; generuje tools/make_map_icons.py), zakázky nemají ikonu.

## Úpravy 2026-10-01

- **Prázdný kanystr zmizí** (viz Bedna a kanystry): `removeVehicleIfEmpty`, prázdný kanystr se do bedny neukládá a vylitý slot se uvolní.
- **Značka dronu na mapě hry** (`scripts/SprayDroneHotspot.lua`): za letu `PlaceableHotspot` s ikonou `gui/icons/mapDrone.dds`, poloha z uzlu dronu;
  vidět na velké mapě i minimapě. Vlek má dál vanilla značku. Ikona dronu je i v plánovači (kreslí se na místě dronu za letu), ikona vleku
  (`mapTrailer.dds`) je teď siluetka vleku s nádrží (`tools/make_map_icons.py`).
- **Plánovač už nekreslí koridor přeletu** (konvexní obálka); legenda upravena. Řádky, které se do plánu nevešly (došla nafta nebo baterie),
  se kreslí červeně (`routeInfo.unplanned`). Plán pole 67 v uložení 12 se zkrátil jen proto, že centrála neměla naftu (`noFuel`); s naftou je
  plánované celé pole (44 řádků, 27 dávek).
- **Čáry ve světě jsou ve výchozím stavu vypnuté**, zapíná je `Alt+5` (`SprayDroneStation.showWorldLines = false`).
- **Pole s remízkem nebo stavbou uprostřed**: řádky se rozdělí tam, kde hustotní mapa pole říká „není pole“ (už dřív), a mezi částmi řádku se
  dron nad překážkou svisle zvedne (`SprayDroneRoute.rowTurn` + `SprayDroneStation.getHopHeight`: svislé paprsky v pásu šířky dronu po 5 m,
  výška = nejvyšší překážka + `obstacleClearance`, nejvýš `maxTransitHeight`), přeletí ji vodorovně a na druhé straně svisle klesne. Bez toho
  by zabrzdila až pojistka za letu. Když se překážka nedá přeletět, zůstává pojistka. Ladicí log `SDT DEBUG přeskok překážky`.
- **Hadice na horní palubě** (`Pump_Discharge`) má hladké oblouky o poloměru 0,15 m (`rounded_path`, vzorky po 4°) a koncovka u navíječe
  se ohýbá celých 90°.
- Vzdálenost, ze které jde bedna ovládat, je 4 m (`activateDistance`).
- Ladění: `probeField` (proč se na poli nesmí stříkat), `status` (i počet kanystrů ve světě), `holdCanister`, `spawnAtCamera`, ...

- **Plnicí hadice na horní desce (2026-10-01)**: klidový tvar už není lomená čára přes `fillHoseLay*`, ale hladká křivka (Catmull-Rom, počítá se v souřadnicích rodiče koncovky, v minimu výšky vodorovná tečna) a posledních 0,16 m (`HOSE_NOZZLE_LEAD`) je rovně v ose koncovky, takže hadice do ní vchází souose (dřív pod ~36°). Stejný rovný nájezd má i visící hadice při plnění dronu. Článků je 96, každý přesahuje o `HOSE_RADIUS·tan(ohyb/2)`. Blender (`hose_rest_path`) počítá tvar stejně jako Lua.
- **Koncovka plnicí hadice jako pistole (2026-10-01)**: modré tělo, černá spoušť a chránič, ocelový ohnutý výtok a otočný přívod hadice šikmo (50°) dozadu a nahoru (`sdt_nozzle.INLET_*`). Hadice do přívodu vchází souose: konec je v `HOSE_INLET_POS`, směr `HOSE_INLET_DIR` (Lua, lokálně v uzlu koncovky), posledních 0,16 m je rovně. Klidová koncovka leží na desce špičkou doleva (`HOSE_PARK_TIP/DIR`), hadice tvoří jednu velkou smyčku (`HOSE_LAY` jen Lay1-5, Lay6-8 = nájezd, konec, špička). Neověřeno ve hře.

- **Hlavní nádrž bez hladinoměru (2026-10-01)**: sloupek s průhlednou trubicí a stupnicí na boku nádrže byl nefunkční, je pryč (`sdt_bigtank.py`, i dekál `_Scale`).
- **Nafta v bedně (Pavel 2026-10-11)**: žádný stojan na naftu ani vyhrazené sloty — naftový kanystr (vlastní `objects/canister/canisterDiesel.xml`: obchod, žlutý, 20 l,
  `fillTriggerVehicle`) je v bedně totéž co koncentrát. Kterýkoli slot pojme obojí, vsátí jde jen u otevřeného víka / vrat otvorem bedny, v dialogu (R) je řádek „Nafta – kanystr“,
  výdej i výroba objektu za vlekem jsou společné (`spawnCanister`, `getSpawnPosition`). Zrušeno: `dieselSlots`, `dieselNode`, `dieselIntake*`, `dieselSpawnDistance`
  v XML i kódu, samostatná aktivace stojanu, druhý dialog, zvláštní otvor kolem aktivačního uzlu, vsátí bez víka, ladicí příkaz `dropDieselOnRack`. Dřív (do 2026-10-11) vsával
  naftu jen Mini a úzkým otvorem bez víka, Middle a Max (`dieselSlots` 0) ji nevsávaly vůbec. Zůstává ruční lití z kanystru do hrdla elektrocentrály (`dieselNeckNode`) i koncentrátové
  nádrže. Ladění: `spawnDiesel`, `spawnSet`. Testy logiky bez hry: `tmp/test_toolbox_parts.py` (Mini, Middle; vsátí nafty i koncentrátu, dialog, sloty, síťový stav).
- **Mini: druhá bedna (2026-10-07)**: místo bývalé šachty baterií přibyla DRUHÁ bedna (`build_mini_toolbox(suffix="2", canister_offset=4)`; od 2026-10-11 s vlastním víkem, aktivací a dialogem,
  viz „Víc samostatných beden“); šachta baterií (`build_bay`/`build_bay_lid`) se postaví na původním místě a pak otočí o 90° a přesune do mezery za generátorem
  (`BAY2_GAP_X/Y`, `_transform_new`), nabíjecí kabel se přepočítává za běhu z pozice `Chest_Socket` a obchází rám centrály (napřed pryč z jeho hloubky, pak stranou mimo jeho šířku, teprve pak zpátky). Celkem slotů: Max a Middle 48, Mini 8.
- **Nalévání z kanystru přes R** (jako vanilla „Doplnit“ / „Zastavit doplňování“, `SprayDroneHandPourActivatable`): hráč s kanystrem v rukou stojí do `HAND_POUR_PLAYER` (2,2 m) od hrdla nádrže, nebo kanystr leží víčkem do `HAND_POUR_LYING` (0,6 m) od hrdla; R spustí / zastaví nalévání (`HAND_POUR_START/STOP`, `pourRate` l/s). Nafta jde do elektrocentrály (`dieselNeckNode`), koncentrát do koncentrátové nádrže (`concentrateNeckNode`). Prázdný kanystr zmizí. Vzdálenost se u drženého kanystru měří od hráče, protože fyzika drženého objektu ho u rámu vleku odtlačí až ~2 m od hrdla. Původní nalévání nakloněním kanystru zůstává. Ověřeno ve hře: nafta 20 → 30 l, kanystr hnojiva vylitý celý. Ladění: `pickCanister`, `pickConcentrate`, `handPour` (stav do logu); teleport (`view`) hráči kanystr z rukou shodí.
- **Vybírání kanystrů** je jediný vanilla dialog skladu objektů `ObjectStorageDialog` (druh + posuvník počtu v jednom okně, jako sklad objektů) — od 2026-10-03 bez druhého kroku „co" (`OptionDialog`), od 2026-10-07 i bez rozdělení na bednu/stojan (viz výš): jedno R u bedny ukáže vše (koncentrát, naftu, vypuštění nádrže) pohromadě. Vyrobený kanystr je chráněný proti vsátí, dokud ho hráč nevezme do ruky (nebo neleží 20 s mimo otvor). Ověřeno (2026-10-03): 3 z 12 z bedny, žádný se nevrátil.
- **Obchod**: kanystry se kupují přes vanilla `multipleItemPurchase` (`objects/canister/multiPurchaseCanister*.xml`, „Množství“ 1–10, mřížka 2 × 5 po 0,32 × 0,24 m); samotné `canister*.xml` mají `showInStore=false`. Ověřeno: 6 ks za 270 € leží u obchodu vedle sebe. Ladění: `shop`, `lookNewest`.
- **Kanystry a obrázky obchodu**: tvar je v `sdt_tanks.canister_shape` (zaoblené tělo prolože `Mesh.loft`, oblé madlo `Mesh.tube` z dna prohlubně pod ním, hrdlo s fazetovaným víčkem) a sdílí ho kanystry v bedně i `build_canister.py`. Obrázky obchodu se kreslí níž než dřív (`STORE_DROP` u vleku, `drop`/`margin` u kanystrů), jako vanilla: vozidla sedí na spodním okraji obrázku. Ladění: `shop` otevře obchod, mody jsou v „Modifikace a DLC“.
- **Truhla s nabíječkou zapuštěná do horní desky**: podlaha truhly je pod deskou (`chest_floor()`), okraj stěn je jen 1,5 cm nad deskou (`CHEST_RIM`) a víko leží v rovině desky. V desce je pro truhlu vyříznutý otvor (`TopDeck_Rear/Front/StripR/StripL`), příčníky pod deskou, kterými truhla prochází, jsou rozdělené (`TopCross_<n>a/b`). Truhla je posunutá o 10 cm doprava (`CHARGER_CELL_X`), aby nezasahovala do levého sloupku. Zásuvka pro kabel je na vnější stěně pod příčníkem (`CHARGER_SOCKET_Z` 0,18 m nad podlahou truhly). Kolize horní desky (`colTopDeck`) zůstává plná, otevřená truhla se tedy přechází jako zakrytá.
- **Lezení po žebříku** je normální pohyb (vanilla `LadderTrigger`, žádná aktivace): spouštěč `ladderTrigger` je potomkem kloubu žebříku (naklání se s ním, geometrie v sekci Žebřík) a `SprayDroneLadder.lua` mu přidá bit hráče a založí `LadderTrigger.new(node)`; ve spouštěči hra hráči vypne gravitaci a chůze / skok ho vynáší. Ověřeno ve hře u starého žebříku zezadu (2026-10-05): chůzí dopředu hráč vyleze na horní desku a přestoupí na ni. Sklopný žebřík na pravém boku (spouštěč vně vleku, hráč leze čelem k vleku) ve hře ověřený není.
- **Pevný ohyb hadice u navíječe při připojování (2026-10-01)**: úsek od `fillHoseStart` (vodítko pod pravou hranou desky) přes bok a lem až na desku (`fillHoseLay3`, `HOSE_FIXED_LAY`) se při animaci nehýbe. Volná prověšená část (`getHangingLine`) začíná nejdřív na konci tohoto úseku (`rest.fixed`, délka klidové křivky k bodu nejblíž Lay3); dřív mohl bod odpojení sjet až k vodítku a křivka ke koncovce pak vedla palubou. Neověřeno ve hře.
- **Podíl koncentrátu 0,05 (2026-10-01)**: hnojivo i herbicid; jeden 20l kanystr udělá 400 l přípravku, tedy víc než nejmenší 300l nádrž (dřív hnojivo 0,25 = 80 l, herbicid 0,10 = 200 l). Šablona, XML vleku a výchozí hodnota v `SprayDroneStation`.
- **Hláška u zamrzlého tahače (2026-10-05)**: sedí-li hráč v tahači, ke kterému je připojený rozložený vlek (kinematický), tahač
  běží a hráč dá plyn nebo brzdu při rychlosti pod 1 km/h, ukáže se (nejvýš jednou za 4 s) „Vlek je rozložený a drží na místě. Slož
  ho, aby tahač mohl odjet.“ (`updateStuckWarning`, jen klient, který řídí). Fyzika se nemění.
- **Nádrže dvou dronů v ukazateli (2026-10-05)**: u dvou dronů se vejdou-li se vanilla řádky vleku, baterie a dvě nádrže do 5 řádků
  (`getSplitTankRows`), jsou „Nádrž dronu 1/2“ samostatné řádky (každý se svým přípravkem a stavem); jinak je jeden řádek
  „Nádrže dronů 40 · 25 l“ se součtem v liště a hodnotami po dronech v titulku (jako u baterií). Max má vždy tři vanilla řádky
  (hlavní nádrže, nafta, koncentrát) + baterie + 2 nádrže = 6, takže má řádek se součtem. Middle a Mini beze změny.
- **Ukazatel naplnění ve vleku (2026-10-01)**: vanilla kreslí nejvýš 5 řádků a od koncentrátové nádrže jich bylo 6, takže nádrž dronu vypadla. Baterie jsou teď jeden řádek „Baterie dron 80 · 100/60 %“ (dílky = všechny baterie v dronu i v nabíječce, plné = připravené; „Baterie (nabíjí)“ při běžící centrále), řádky: nafta, baterie, hlavní nádrž, koncentrát, „Nádrž dronu“ (bez baterie v dronu s poznámkou „bez baterie“). Text „Nabíječka“ zmizel i z HUD (`sdt_hud_power` = „Baterie v nabíječce“). Neověřeno ve hře.
- Ladění: `spawnSet` = dva plné kanystry hnojiva, herbicidu a nafty v řadě 2 m za kamerou (mimo dosah sání bedny).

## Malý vlek (Mini) a skládací bedna s dronem

Druhý vlek (`vehicles/sprayDroneTrailerMini`, 300 l, dron S, 3 baterie, dvě bedny na 4 kanystry) má všechno na jedné palubě, bez horní
desky. Model staví `blender/build_trailer_mini.py` (nad `build_trailer_middle.py`), export `export_mini_mod.py`, šablona
`blender/templates/sprayDroneTrailerMini.xml.in`, bez okna `headless_mini.py -- build|render|export`. Rozměry (z modelu, `<size>` zahrnuje složený dron):
**2,60 m široký** (paluba 1,86 m, kola s blatníky vně rámu), 5,99 m dlouhý, 1,66 m vysoký, `lengthOffset` 1,52. Uspořádání shora (délka paluby 4,0 m, -Y vpředu):
centrála vlevo a indukční nádrž vpravo, za nimi čerpadlo, mixér a šachta baterií (otočená napříč za centrálou),
uprostřed **nízká hranatá nádrž** 0,90 x 0,98 x 0,369 m (vnitřní objem 299,98 l, `pad_tank_liters`; hrdlo a odvzdušnění nahoře, šířku určují
víka beden na kanystry, která se otevírají těsně k ní) mezi dvěma **bednami na kanystry** u lemů paluby (x ±0,545..0,865, uzly `toolboxCanister1-4`
vpravo (-X), `5-8` vlevo (+X)), vpravo za nádrží **navíječ hadice** (osa podél vleku, `REEL_X` -0,72, `REEL_Y` -0,20) a vzadu **bedna s dronem**
přes celou šířku vleku. Boky nádrže zakrývají bedny na kanystry, proto je jediný popisek (objem + výstražný štítek, regiony `tankVol300` /
`tankPlate300` v atlasu `sdt_decals`) na její horní ploše, čitelný zezadu. **Výtlak čerpadla** (`Pump_Discharge`) nevede přes nádrž: z výpusti krátce nahoru, přes čelo nádrže
k mezeře mezi nádrží a pravou bednou (x -0,50), tou **nízko při palubě** (1,2 cm nad ní) dozadu, za zadní stěnou pravé bedny zalomí k navíječi a stoupá k otočnému přívodu
na předním konci jeho osy; bedny, nádrž ani hadice se s ním nekříží (BVH). Těžiště: zátěž oje vychází z hrubého odhadu hmot ~12-14 % (`HITCH_LOAD` 0,14).

**Bedny na kanystry** (`build_mini_toolbox`) jsou dvě, každá s vlastním víkem (`toolboxLid` / `toolboxLid2`), aktivačním uzlem (`toolboxActivateNode` /
`toolboxActivateNode2`) a dialogem jen se svými 4 sloty (pravá 1-4, levá 5-8; XML `<box>`, viz „Víc samostatných beden“). Závěs víka je u obou na hraně u nádrže,
víko se odklápí směrem k nádrži o `openAngle="96"` (kladné natočení kolem lokální osy X pivotu u obou). Levá bedna se staví na `BOX_X = BOX2_X`
(závěs na vnější hraně) a pak se celá, i s pivotem víka a aktivačním uzlem, otočí o 180° kolem svého středu (`_transform_new`), takže závěs padne k nádrži
a pivot dostane Rz -90° (i3d `rotation="0 -90 0"` proti `0 90 0` u pravé). 105° zasahovalo špičkou víka ~3,5 cm do nádrže
(BVH kontrola, nádrž je ±0,455 m), od 102° víko do nádrže vniká; 96° nechá odstup. Otevřená víka se nekříží s ničím dalším (kontrola BVH víka proti všem
ostatním meshům, `tmp/mini/check_lids.py`). Víka se sama nezavírají (viz „Ovládání bedny“).

**Bedna s dronem** (`build_pad_crate`, `build_side_panels`) má tři ploché panely P (přední stěna), H (střecha), Z (zadní stěna) na řetězu čepů
`padHingeZ -> padHingeH -> padHingeP` (stejná osa X, úhly se sčítají; v i3d 90° = složeno), po stranách **dvě plechové boční stěny** `padSideL` / `padSideR` a šest
nožiček (`padLeg1-6`). Panely jsou dvouvrstvé: horní strana (uvnitř bedny, po rozložení pochozí a pojezdová)
je pochozí plech `SDT_TopDeck`, spodní strana (ve složené bedně VENKU) zelený lak `SDT_CrateGreen` s černým lemem po bocích a na volných hranách,
třemi žebry, kloubovými válečky na čepech Z/H a H/P, dvěma zámky na zadní a přední stěně, madlem a rohovými patkami; v přední stěně je při spodní
hraně výřez pro hadici (`HOSE_NOTCH_*`, poloha z klidové hadice). **Boční stěny** (0,82 m vysoké, mezi přední a zadní stěnou bedny; zelený plech 6 mm venku, pochozí plech uvnitř
v rámu 34 mm, dvě vnější žebra, kloubové válečky na čepu a dva zámky nahoře) stojí ve složeném stavu svisle na lemu paluby (čep `padSideL/R` v x ±0,93, z paluby + 1,25 cm) a drží
bednu po stranách. Dron stojí uvnitř přímo na palubě, otočený o `DRONE_EXTRA_ROT` 90° (šířka vleku místo délky; jeho půdorys je 1,38 x 1,28 m), kořen `<prefix>Root` je pod uzlem
`droneCarrier`, který leží přesně v ose trupu. Po rozložení tvoří panely plošinu 1,86 x 3,04 m, na jejím prostředním panelu H je heliport
(kruh, mezikruží, písmeno H s rameny podél vleku); dron dosedá lyžinami na čáry H (`CRATE_SETTLE` -0,011). Pohyb řídí `scripts/SprayDronePad.lua`
z času skládání vleku (`getFoldAnimTime`, 0 = rozloženo), animace `foldTrailer` trvá 10 s (do 2026-10-29 12 s, z toho 2 s rezerva na skládání dronu, který se s Mini už neskládá), v XML se animuje jen víko šachty a zvuky:

| čas (s) / čas skládání | děj |
|---|---|
| 10 -> 9 / 1 -> 0,9 | otevře se víko šachty baterií (`chargerLid`, závěs na straně centrály, víko se zvedá a sklápí k ní), kabel se zapojí |
| 9 -> 8,6 / 0,9 -> 0,86 | bedna s dronem přestane být zajištěná (`securedFoldTime = 9 / 10`) |
| 8,6 -> 0,6 / 0,86 -> 0,06 | `SprayDronePad` (D 0..1, `foldStart`/`foldEnd`): boční stěny se kolem spodní hrany na lemu paluby vyklopí ven a sklopí k zemi (D 0-0,14; úhel od svislice 100-165° se dorovná podle terénu pod stěnou, aby spodní hrana zůstala ≥ 1,2 cm nad ním, pochozí vnitřní strana skončí nahoře); panely se sklopí do roviny všechny tři o stejný úhel, takže stěna P jede od dronu pryč a střecha H nad ním (0,14-0,38, dron stojí na místě; v posledních 20 % se plynule objeví nožičky, uzel `padLeg` se škáluje 0 -> 1); nožičky se natáhnou a plošina se vyrovná (0,38-0,53); dron se s bednou nehýbe, zůstává v bedně (D 0,53-1 je klidová pauza) |
| 0,6 -> 0 / 0,06 -> 0 | krátká rezerva (`sprayDrone#trailerFoldEnd`); dron se s vlekem nerozkládá ani neskládá |

Dron má dvě polohy (bedna / plošina, `pad.onPlate`) a mezi nimi ho přendává jen hráč: R s prázdnýma rukama u druhého místa (okamžitě, bez animace,
`SprayDronePadSlots.moveMiniTo` → `SprayDronePad.setDroneOnPlate` nastaví rozložení ramen rovnou na cíl, vrtule do klidu, hadici na navíječ), nebo jako předmět.
Vlek s dronem na plošině nejde složit (`sdt_warning_padDroneOnPlate`), rozložení dron na plošinu nedává. Podrobně `docs/NAVRH-dron-predmet.md` kap. 12.

**Mini v obchodě** (od 2026-10-13): `SprayDronePad.openInShop` nastaví v `SHOP_CONFIG` čas skládání na 0 (`foldable.loadedFoldAnimTime`), takže se vlek v obchodě a v konfiguraci ukáže
rozložený, dron s rozloženými vrtulemi stojí na plošině a jde vybrat vrtule, baterie i dron. Koupený vlek se načítá znovu mimo obchod a začíná složený. **Neověřeno ve hře**
(chování nožiček plošiny a hádání terénu v obchodě, náklon podle platformy).

Skládání je opačně (bedna se složí kolem dronu v bedně a jako poslední se boční stěny zvednou zpět na lem paluby).
Panely dronem neprocházejí (BVH kontrola v Blenderu po 0,01 kroku D, emulace `applyPose`: `tmp/mini/pa/check_panels.py`), boční stěny se nekříží s ničím ani při plném vyklopení; po
rozložení se panel Z jen dotýká zadního nosníku paluby v čepu (plošný dotyk, žádný průnik). Při rozkládání jede stěna P nejdál 0,2 m před čelo bedny a to ve výšce nad 0,55 m nad
palubou. Blok `vehicle.sprayDrone.pad` (`foldStart`, `foldEnd`, `legRest`, `legFoot`, `maxLegLength`, `maxHeightDiff`, `checkHeight`, `liftHeight`,
`droneSettle`, `droneYaw`) píše export z konstant modelu (`CLAMP_TIME`, `DRONE_UNFOLD_TIME`, `CRATE_*`); šířka a hloubka plošiny se čtou z uzlů
nožiček (součet lokálních translací, škálování `padLeg` ho neovlivní). Uzly: `padAnchor`, `padHingeZ/H/P/End`, `droneCarrier`, `padSideL/R`, `padLeg<i>` (pivot na spodku plošiny,
pouzdro `Crate_LegSleeve<i>` je jeho potomek, ve složeném stavu skryté), `padLegRod<i>` (škáluje se po Y), `padLegFoot<i>`; nožičky jsou v i3d skryté (`hidden_nodes`) a skript je ukazuje.
Nožičky se natáhnou na terén a plošina zůstane vodorovná i na šikmém vleku; kontrola před rozložením (`SprayDronePad.checkDeploy`: terén, `overlapBox` pod plošinou a
nad bednou, dosah hadice) a obrys plošiny ve světě (zelený / červený) jsou z dřívější desky. Boční stěny jedou jen v lokálních souřadnicích vleku a terén měří jen kvůli
úhlu sklopení (`SprayDronePad.applySide`, `getSideFall`).

**Polepy** (atlas `sdt_decals`, regiony v `blender/decal_layout.py`): boční stěny nesou na vnější straně siluetu dronu s nápisem „SPRAY DRONE“ (`Crate_SideLogoL/R`), výstražný pruh při horní hraně,
štítek „SD-S“ a pruh na pochozí straně; panely bedny: Z nápis „SPRAY DRONE SERVICE“, siluetu a pruh, H velkou siluetu dronu s nápisem a pruh u přední hrany, P nápis, štítek a pruh;
dále reflexní pruhy na čelním a zadním nosníku (`Decal_StripeFront`, `Decal_StripeRearL/R`) a štítek koncentrátu na víkách beden (`Decal_LidConc`).

**Orientace dronu a hadice**: dron se při přejezdu otočí o `-droneYaw` zpět do osy v i3d (nos po směru jízdy, `homeYaw` vychází z rodiče +
pevného offsetu, takže sedí). Hrdlo je na pravé straně trupu (-X) a navíječ je také na -X straně, takže hadice (`hoseVia` jako u Middle S)
přechází přes přední hranu trupu na straně hrdla. Plnicí hrdlo, lůžko baterie a výřez v trupu stavěl `build_drone_service_parts` ve světových
souřadnicích dronu v (0, 0) po otočení dronu, takže u Mini ležely ~0,5 m vedle trupu; `build_drone_service_parts_mini` posune souřadnice o
`DRONE_Y` a volá se před otočením.
Hadice je navinutá na modrém navíječi vpravo za nádrží (osa podél vleku: buben mezi dvěma bočnicemi, konzoly na obou koncích osy, otočný přívod na
předním konci osy u nádrže, kam sestupuje výtlak čerpadla; vodítko ve tvaru brány za bočnicí; `fillHoseCoil`). Vychází z poslední otáčky vespod
stranou ke středu vleku (`HOSE_START` = spodek vinutí u zadní bočnice, směr +X mezi bočnicemi) a plynule zatáčí dozadu: `fillHoseLay1-3` je pevný úsek
(oblouk od navíječe a rovina pod bednou, výřez v přední stěně bedny je v místě jeho průchodu), `fillHoseLay4-8` hladká smyčka na zadní části paluby,
koncovka v `fillHoseParkPos`. Klidovou křivku (Catmull-Rom jako `SprayDroneService.getRestLine`) kontroluje `blender/tune_mini_hose.py`: volná
část 2,48 m proti potřebným 2,34 m (rezerva 0,14 m), nejmenší poloměr ohybu 0,186 m (~ 4,6 x průměr), od nádrže, beden a navíječe odstup >= 0,2 m
(vinutí na bubnu přiléhá z konstrukce). `SprayDronePad.hoseReaches` počítá volnou délku přímo z té křivky (`SprayDroneStation.getHoseRestLine`),
ne z bodů Lay. Zbývající průnik: hadice leží pod složeným dronem pod jeho lyžinou (uvnitř zavřené bedny, nikdy není vidět).

**Podvozek** (`build_suspension` a `build_fenders` v `build_trailer_mini.py`, podle Utili Trailer 2; velký vlek má původní): kola jsou **vně rámu** (`TRACK_X` 1,11, vnitřní líc pneu
0,95 těsně za lemem paluby 0,93), nad nimi pevné **blatníky** `Fender_L/R` (oblouk -18..198°, plech 8 mm, přesah 3 cm, držáky k lemu, zástěra za kolem), takže vlek měří 2,60 m. Hranatá
náprava (y -0,45, pod zadní částí nádrže a beden) s krátkými čepy k brzdovému bubnu a náboji u kola (potomci uzlů `wheelFront*`, jedou s odpruženým kolem), na každé straně pod rámem
svazek pěti listů pružin (`Leaf_<strana><k>`, loft po Y) s oky, úchyty k palubě a zadním třmenem, přítlačná deska a třmenové šrouby. Kola: vanilla `320_60R12` (R 0,354, šířka 0,32),
horní hrana kola je v blatníku (mezera od 2026-10-13 11 cm kvůli o 3 cm větší pneu Destination Farm, dřív 8 cm; zdvih odpružení 0,07); kola samotná generuje hra z konfigurace (modelovaná kola jsou jen náhled). Zátěž oje vychází ~14 % (`HITCH_LOAD`).
**Pneu a disky** (od 2026-10-13, Pavel: bez výběru, jedna silniční pneu úměrná vleku a ne sterilní disky): `wheelConfigurations` v šabloně má jen `DEFAULT`
(`isDefault`) s pevným souborem pneu (`<wheel filename=...>`, `physics#yOffset` = rozdíl poloměru proti modelu, aby zůstal dotyk se zemí) a vlastním diskem
(`<outerRim filename="wheels/sdtRim22.i3d|sdtRim15.i3d" node="0|0" (levé) / "0|1" (pravé) widthAndDiam=.../>`, `<innerRim filename="-"/>`).
Max: Conti Hybrid HD3 315/80 R22,5 (`tireType` street, r 0,54, yOffset 0,01), disk 22,5 x 9 `sdtRim22`; Mini a Middle: Lizard Destination Farm 280/70 R15
(kategorie TRAILER, `street`, r 0,385, yOffset 0,031; model v Blenderu zůstává v poloměru 0,354, poloha os a blatníků se nemění), disk 15,5 x 8 `sdtRim15`.
**Disky** staví `blender/sdt_rims.py` (ráfek s přírubami, lisovaný talíř s průchozími otvory (Max 10 oválných, Mini/Middle 6), náboj, matice s podložkami,
u Maxe oranžové ukazatele povolení matic, krytka náboje se šrouby, ventilek) a exportuje `blender/export_rims.py` (`blender.exe -b --python blender\export_rims.py [-- render]`)
do `wheels/sdtRim22.i3d` a `sdtRim15.i3d` (vehicleShader bez varianty, barva a detail z `materialTemplates.xml`; tentýž tvar je náhled kola v modelu,
`build_wheel_previews` / `build_pad_*`). Pořadí uzlů v i3d (levý `0|0`, pravý `0|1`) hlídá export. **Neověřeno ve hře** (načtení disku z modu, měřítko vůči pneu).
Dřívější id kol z uložených her (`DEFAULT_CONTINENTAL_contiHybridHT3`, `DEFAULT_TRELLEBORG_T421`, `TRELLEBORG_*`, `BKT_*`, `CONTINENTAL_*`) zůstávají v XML jako skryté
konfigurace (`isSelectable="false"`, `baseConfig="DEFAULT"`, seznam `LEGACY_WHEEL_IDS` v `build_trailer_*.py`), takže uložený vlek dostane nová kola, ne žádná
(hlídá `tools/check_save.py`).

**Kolize** (`equipment_collisions`, z konstant modelu): `colTank`, `colToolbox`, `colToolbox2`, `colHoseReel`, `colGenerator`, `colInductionTank`, `colPump`, `colMixer`, `colBatteryBay`,
`colDrawbar` (oj), `colJockeyWheel`. Bedna s dronem, boční stěny, nožičky a blatníky kolizní kvádr nemají: bedna se rozkládá do plošiny a statický kvádr by v ní zůstal jako neviditelná zeď
(kola a blatníky drží fyzika kol). Vyplnění kvádrů viditelnou geometrií 77-100 %, žádný kvádr nepokrývá volné pochozí místo.

**Oj** má 1,85 m (`COUPLER_Y` -4,45, hlava spojky, brzda a kabel z `build_trailer_middle.py` se staví v rámu velkého vleku
a posunou se, opěrné kolečko `JOCKEY_Y = COUPLER_Y + 0,875`), čelo vleku se u velkých tahačů dotkne pneumatiky až při 46-59°. Sání čerpadla
jde k mixéru podél osy Y těsně u levého okraje (mimo rám centrály).

## Velký tandemový vlek XL / Max

Třetí vlek `vehicles/sprayDroneTrailerMax` (`blender/build_trailer_max.py`, export `export_max_mod.py`, šablona `sprayDroneTrailerMax.xml.in`;
headless `headless_max.py -- build render|export`). Skládá se z `build_trailer_middle.py` (text-patche + přepsané funkce), stejně jako Mini.

- **Rozměry** (z modelu, `<size>` bez dronů): 3,09 m široký, 9,83 m dlouhý, 3,85 m vysoký (madla žebříku nad deskou), `lengthOffset` −1,79.
- **Rozložení po Y** (−Y vpřed): oj → nádrž A →
  **uprostřed mezi nádržemi** indukční nádrž s čerpadlem a mixérem (vpravo) a elektrocentrála (vlevo) → nádrž B (od y 3,20, její výpust je
  napojený na sání čerpadla) → skříň na kanystry na zadním okraji (y 6,08…6,50, `BASE_Y1` 6,50). Nahoře dvě přistávací plochy (`PAD_Y` −0,10 / 5,15),
  mezi nimi servisní zóna: truhla nabíječky u levého okraje a **dva navíječe v kapsách horní desky po obou stranách truhly** (A před ní, B za ní, zrcadlově
  podle jejího středu, osa podél vleku v x 0,43; každý dron má svou hadici, hrdlo dronu je na straně, kde stojí jeho navíječ).
- **Nádrže**: dvě ležaté PE cisterny (3000 nebo 5000 l podle konfigurace) s **oválným průřezem** (superelipsa `OVAL_N` 3, zaoblená čela, popruhy a vylisovaná žebra, `build_oval_tank`)
  místo hranatých beden. Obalový kvádr (šířka, výška, délka z `decal_layout.BOX_GEOM`), výpust, hrdlo, uzly `tankMain<litry>[B]`, kolize `colTank*` a nálepky zůstaly jako u hranaté nádrže,
  skutečný objem tvaru je ~90 % obalu (kapacita je v XML, model je jen vzhled).
- **Kola**: pneu 385/65 R22,5 v modelu (r 0,536, šířka 0,385; ve hře Hybrid HD3 315/80 R22,5, viz „Pneu a disky“), vně rámu (`TRACK_X` 1,27), nad nimi tandemové blatníky se zástěrkami; paluba kvůli tomu
  ve výšce 1,00 m (`_DZ` = +0,28 proti Middle, horní plošina 2,78 m). V XML `tireCategories="TRUCK"` + `tireCombination` contiHybridHT3
  (jako vanilla motherBin4000), bez `outerRim`. Tandem `AXLE_Y` 2,95 / 4,40 pod zadní nádrž (kladná váha na oji ~4 %).
- **Oj podle vanilla Farmtech DPW 1800** (`build_drawbar`, tvar z `dpw1800.i3d`): plochý A-rám z ocelových pásnic 75 × 75 mm, který se z kořene (osa pásnice x ±0,52) sbíhá do krátké
  hlavy s tažným okem (`attacherJoint` ve středu oka, `COUPLER_Z` 0,70, oko i rám ve vodorovné rovině), tři příčky, délka od čela rámu k oku 2,0 m (`DRAWBAR_LEN`, DPW 1,95 m), podpěrné
  kolečko (`jockeyWheel`) 1,35 m za okem. **Pevná, bez předních kol a bez otočné nápravy.** Kolize `colDrawbar` (y −2,85…−1,05) a `colJockeyWheel`.
  **Volba zapřažení v obchodě** (od 2026-10-13, Pavel: „za auto, nebo oj za náklaďák / traktor; pickup to utáhne“): `inputAttacherJointConfigurations` s `TRACTOR`
  (výchozí; spojky `trailer` a `trailerLow`, skupina `drawbarTractorSet`: tažné oko na přírubě se čtyřmi šrouby, pojistný řetěz s hákem, držák vzduchových spojek
  `airIn` červená a `airOut` žlutá s vedením podél pásnice, zaparkované spojky `*_detached`) a `CAR` (příplatek 400 €; spojka `trailerCar`, skupina `drawbarCarSet`: kulová
  hlava s nájezdovou brzdou, ruční brzda, brzdové táhlo a pojistné lanko jako u Middle). Skupina `drawbarCarSet` je v i3d skrytá (`hide_nodes`), zapíná ji `objectChange`.
  Elektrika (`electric` / `electric_detached`, držák na hlavě oje a kabel od zásuvky na čele rámu) je společná. `<connectionHoses>` (vzduch + elektrika, délka 1,6 m) jako u
  vanilla DPW 1800, `inputAttacherJointIndices="1 2"` = jen spojky za traktor. Překlady `sdt_hitch_tractor` / `sdt_hitch_car`. **Neověřeno ve hře** (zapřažení za pickup,
  zobrazení hadic u tahače, výběr konfigurace v obchodě); Škodovka vlek neutáhne (to hlídá hra podle hmotnosti a spojky, ne mod).
- **Víka kapes navíječů** (Max, `build_reel_lid`, uzly `hoseLidHinge` / `hoseLidHingeB`): kapsa každého navíječe má víko na závěsu na vnější straně (hadice vychází z vnitřní),
  které se po složení vleku zaklapne přes kapsu (animace `foldLadder`, 2,1–2,6 s hned po úchytech lyží, `hose_lid_parts_xml` v `export_max_mod.py`, zvuky `coverMetalOpen` / `metalClose`).
  V i3d je víko otevřené (100°), kapsa se zavře jen vizuálně (kolize `colHoseReel` zůstává). Tohle jsou „místa na hadici“ z Pavlova bodu 2, jen u Maxu. **Neověřeno ve hře.**
- **Robustní rám**: I-nosníky s pásnicemi, deset příčníků pod palubou, boční lem 0,24 m, listové pružiny (6 listů), ochrana proti podjetí.
- **Žebřík**: stejný jako u Middle, viz „Žebřík“ (vpravo v y 1,75 před předním blatníkem tandemu). Nohy nemá, viz „Náklon vleku“.
- **Skříň na kanystry**: stejná jako u Middle, viz „Skříň na kanystry (Middle a Max)“ v sekci Bedna a kanystry (48 slotů, rolovací vrata se zasouvají nahoru do pouzdra, nafta jako koncentrát); sahá až pod
  horní plošinu. `SprayDroneToolbox.MAX_SLOTS` je 48.
- **Lua**: oba drony viz sekce „Dva drony na Maxu“ níže. Nic z Maxu nebylo ve hře ověřeno.

### Dva drony na Maxu a pohled z dronu (2026-10-04, Lua, nic nebylo ve hře ověřeno)

Implementace podle `docs/DVA_DRONY_NAVRH.md` (varianta C), s rozhodnutími Pavla z kap. 9 (dvě hadice, žádná fronta):

- **Mechanismus** (`scripts/SprayDroneFields.lua`, `SprayDroneDrones.lua`): dron 1 je přímo `spec` vozidla, dron 2 je pohled
  (`createView`), který sdílená pole čte a zapisuje do `spec` a ostatní drží sám. `SprayDroneDrones.runAs(self, k, fn, ...)` na dobu volání
  dosadí pohled dronu k, `forEach` volá fn pro oba, `getRoot` vrací vozidlový spec. Pole se klasifikují v `SprayDroneFields`
  (`tools/audit_spec_fields.py` hlídá, že je každé použité `spec.<jméno>` v právě jednom seznamu; `tools/test_split.py` zkouší pohled).
  **Pravidlo**: funkce, která sahá na per-drone pole (stav, uzly, trasa, hadice), se volá jen v kontextu dronu (`runAs` / `forEach`).
  Middle a Mini mají `numDrones = 1` a běží týmž kódem.
- **XML**: `drone(?)#slot="2"` (druhý dron téže varianty; z bloku se berou jen uzly, zvuk, efekty, hadice – parametry letu jsou
  ze slotu 1), `#hosePrefix` (`fillHose` / `fillHoseB`), `#cameraIndex`, `#cameraNode`, `#cameraTrans`, `#cameraPitch`, `power#slots` (šachty
  nabíječky, Max 8), `sprayDrone#layerGap`. `numDrones = 2` jen když je v i3d kořen dronu 2.
- **Let**: `START` / `RETURN_HOME` mají `droneIndex` (0 = všechny drony v misi, tlačítka `Alt+8` / `Alt+0` startují a vracejí oba),
  nastavení `activeDrones` (plánovač, „Drony v misi“). Práci dělí `SprayDroneRoute.splitLegs`: dron 1 bere začátek seznamu legů, dron 2 zbytek
  pozpátku (od vzdáleného konce pole), řez podle odhadu času obou; přepočítává se při každé dávce ze zbývající práce (`buildLegs` → `buildAllLegs`
  od domova dronu 1 + řez), rozpracované úseky druhého dronu se vynechají (`getReservedSegments`, `SprayDroneRoute.reserved`).
  Pokrytí je sdílené. „Pole hotové“ ohlásí až ten, kdo přistane poslední, když nic nezbývá (`startNextBatch`). Druhý dron letí při přeletech o
  `LAYER_GAP` (6 m) výš (`layerOffset` v `getFlightParams`, `makeTransit`, `getHopHeight`); vzlet čeká, když jiný dron letí níž než 8 m do
  8 m od plošiny (`getIsOtherDroneNearPad`).
- **Servis**: každý dron má svou hadici (`hose`, `hoseT` jsou per-drone, uzly `fillHose…` / `fillHoseB…`), čerpadlo je jedno (při plnění obou se
  průtok dělí), baterie jsou jeden fond (`battery.drone` = dron, ve kterém je baterie, při `slot = 0`), nabíječka 8 šachet
  (`numBatterySlots`, bity slotu `batterySlotBits`).
- **Přenos a uložení**: do `writeState` se pro `numDrones > 1` za blok dronu 1 přilepí blok dronu 2 (`writeDroneBlock`), `battery.drone`
  a `transferDrone`; jednodronový proud je beze změny. Savegame: dron 1 jako dřív, dron 2 v `.drone2#…`, `.battery(?)#drone`,
  `.flightSettings#activeDrones`. Události `SprayDroneCommandEvent` a `SprayDroneServiceEvent` nesou `droneIndex`, `SprayDroneSettingsEvent`
  `activeDrones`.
- **Natočení dronu na plošině**: přední dron na Maxu sedí nosem dozadu; `getHomeYaw` přičítá `homeYawOffset` (natočení kořene dronu vůči rodiči),
  takže se při vzletu nepřetočí.
- **Pohled z dronu**: kamery `droneCamera1/2` (uzly kamer v i3d, XML `<cameras>` čísla 2 a 3) se za běhu připojí pod uzel náklonu zvolené varianty dronu
  (`attachDroneCamera`, poloha `cameraTrans`, sklon `cameraPitch`) a letí s dronem. Akce `SDT_DRONE_VIEW` (`Alt+9`, jen ve vleku) přepíná
  vnější pohled → dron 1 → dron 2 → vnější pohled. V pohledu dronu se myší rozhlíží (kamery jsou `rotatable`). Klávesa `C` (přepis `setActiveCameraIndex`) tam přepíná mezi pohledem z dronu a pohledem
  na dron zvenku (kamery `droneOutCamera1/2` kolem středu otáčení `droneOutTarget1/2`, který se za běhu připojí pod uzel dronu, XML `outCameraIndex` 4 a 5, `outTargetNode`), jako u traktoru; v ostatních pohledech vrací vnější pohled vleku.
  Vystoupení (E) nebo `Alt+9` vrací k vleku. **Neověřeno ve hře.**
- Zbývá ověřit ve hře (vše jen syntakticky a lupa testem): načtení Maxu, rozložení, vzlet obou dronů, dělení pole, plnění dvou hadic, přepnutí
  kamery, uložení a multiplayer. Dynamická pojistka „dron v cestě“ (kap. 2.5 bod 4 návrhu) se neimplementovala.

## Revize Lua jádra (2026-10-05, balík a; ve hře neověřeno)

- **Ladění je vypnuté** (`SprayDroneDebug.ENABLED = false`, kód zůstal); zapnout ho jde přepsáním na `true`. Logy `SDT DEBUG plán` a
  `přeskok překážky` jsou navíc za `SprayDroneStation.DEBUG_FLIGHT`.
- **Pojistka za letu má strop**: stoupání před překážkou končí v `maxTransitHeight + 20 m` (`GUARD_CEILING_MARGIN`). Za letu dron zruší misi,
  vrátí se a ohlásí „překážka“ (`STATUS_OBSTACLE`); při návratu paprsky 5 s ignoruje (`GUARD_GIVE_UP_TIME`). Paprsky se počítají po 100 ms,
  energie na návrat po 150 ms.
- **Max s `activeDrones = 1`**: náhled a souhrn plánovače počítají jen dron 1 (dron 2 dostane prázdný seznam). Při dvou dronech se náhled
  dělí vždy s žadatelem 1, takže oba nedostanou celé pole.
- **Hlášení konce mise**: každá změna statusu na nenulový se hráči z farmy vleku ukáže jako ingame notifikace (u dvou dronů s číslem; „pole
  hotové“ jen jednou). Nový status `sdt_status_generatorOff`: dron čeká na nabití baterie, ale centrála je vypnutá, mise končí hned.
- **Nápověda akcí**: Alt+1 (vypustit dron) a Alt+2 (přečerpat do IBC) se zobrazí jen, když to jde (nebo právě běží); B (centrála) mění text
  „Zapnout / Vypnout elektrocentrálu“. Stav se do inputu zapisuje jen při změně.
- **Skládání vleku s letícím dronem**: `getIsFoldAllowed` pošle dron domů jen při pokusu o skládání (směr > 0), rozložení nic nevyvolá.
- **Žebřík**: spouštěč lezení je zapnutý jen při rozloženém vleku (`SprayDroneLadder.ACTIVE_UNTIL`), hráč na žebříku se při vypnutí
  a smazání vleku pustí.
- **Multiplayer**: události Command, Service, Area a Settings server provede jen hráči z farmy, která k vleku smí; plocha má nejvýš 64 bodů
  a nečitelné souřadnice se zahodí; `ToolboxEvent.COUNT_BITS` je 6. Za letu se každý snímek posílá jen poloha dronů (`positionDirtyFlag`),
  celý stav jednou za 500 ms a při změně.
- **Zvuk** (vzorky se berou z XML, bez nich vlek mlčí): `<sounds>` vleku má navíc `pump` (smyčka při plnění dronu), `transfer` (smyčka při
  přečerpávání), `hoseAttach` / `hoseDetach` (hadice) a `batteryInsert` (výměna baterie); dron (`<drone><sounds>` nebo společné) má `spray`
  (smyčka při postřiku). Formát jako u `generator` / `rotor` (`template`, `linkNode`, `innerRadius`, `outerRadius`, `volumeScale`, `pitchScale`).
  Druhý dron má rotor o 3 % níž a o 170 ms později.
- **Hotspot dronu** na mapě: název „Dron“ / „Dron 1“ / „Dron 2“, barva podle dronu, menší ikona. **XML**: nový nepovinný atribut
  `sprayDrone#batteryReserve` (rezerva baterie při plánování v sekundách letu, výchozí 30).

### Třetí kolo oprav 2026-10-14

- Rozložení Mini blokovala kontrola dosahu hadice (potřeba 2,40 m, volných 2,35 m): `HOSE_SLACK` 1,10, `HOSE_ARC` 0,12 v `SprayDronePad.lua`. Ladicí příkaz `foldCheck` vypíše důvod, proč `getIsFoldAllowed` odmítá.
- Listy dronů: `build_drone.blade_fold_angles` počítá složený úhel i otočení do rozložené polohy (`sdt_unfold_delta`, čte ho `drone_fold_parts`); dřív končily oba listy v rozloženém stavu přes sebe. Mini (dron S): složené listy míří podél ramene dovnitř, 10° od sebe (režim "pair").
- Obchod, Mini: bedna je složená, víko a přední stěna rozložené do jedné řady se zadní stěnou (`SprayDronePad.openInShop`, `pad.shopPose`); boční stěny složené.
- Mini, hadice u dronu: `hoseVia` posunuto na 0,145 0,22 0,34, ať hadice nejde skrz nos dronu. Neověřeno ve hře (nepodařilo se vynutit připojení hadice).

### Čtvrté kolo (2026-10-15): Max bez nožiček, dvě centrály, kulaté nádrže (jen model a Lua, ve hře neověřeno)

- Nožičky pryč u Middle i Maxu (model, export, Lua, překlady); Mini si nožičky plošiny nechává.
- **Max, rozložení po Y**: oj → přední paluba s elektrocentrálami (BASE_Y0 −1,85, centrály před horní plošinou, kanystry se do nich lijí shora i zepředu) → nádrž A → mezera 1,34 m s mixérem
  (čerpadlo, indukční nádrž) → nádrž B → skříň na kanystry. Horní plošina, truhla nabíječky a navíječe zůstaly nad mezerou (střed y 2,47).
- **Nádrže**: válcové se zaoblenými dny jako malé u Middle (`build_round_tank`, 3000 l: R 0,68 × 1,95 m, 5000 l: R 0,74 × 2,45 m, objem tvaru ~66–85 % jmenovitého), o 8 % zploštělé (`TANK_SQUASH`), aby výtlačná hadice navíječů vedla pod horní deskou nad nádrží. Čelo zadní nádrže pevně v y 3,14, přední nádrž končí v y 1,80 (její čelo se mění s velikostí).
- **Centrály**: dvě (druhá zrcadlově vpravo, nálepky čitelné), konfigurace v obchodě `sprayDroneGenerator` (1 výchozí, 2 za 3 500 €, `count`): dvě nabíjejí baterie dvakrát rychleji (`chargeRate` × počet) a spotřebují za čas dvakrát tolik (na baterii stejně), nádrž na naftu je `dieselPerGenerator` (30 l) × počet.
  Druhá centrála je celá pod uzlem `generator2` (objectChange i `colGenerator2`), má vlastní výfuk `generatorExhaust2` (kouř) a hrdlo `dieselNeckNode2` (nalévání nafty kanystrem bere nejbližší hrdlo, `getNearestNeck`); zvuk motoru hraje jen u první.
  Všechny kanystry se do centrál lijí shora, `dieselFillRootNode` kryje obě.
- **Kabely nabíječky** jsou napevno (průchodka v zadní stěně nádrže centrály a průchodka u truhly, žádné zástrčky), vidět i složené: `chargerCable` ke první, `chargerCable2` (pod `generator2`) ke druhé; vedou z truhly vnitřkem paluby podél levého lemu dopředu a zezadu do centrál.

### Spojení s dronem (2026-10-15): dosah, anténa, RTK, relé tyč, tablet (Lua, XML a modely; ve hře neověřeno)

- **Základní dosah** poloviční: `maxRange` S 300 / M 450 / L 600 m (Mini 300), společný strop 750 m. Dosah z baterie (`getBatteryRange`) zůstává, strop je dosah rádia.
- **Anténa** (jen Middle a Max, konfigurace `sprayDroneAntenna`, `#rangeBonus`): základní 1,0, zesílená 1,35 (1 200 €), velká směrová 1,7 (3 000 €). Násobí `maxRange` při načtení (`SprayDroneStation.getConfigValue`). Model antény na vleku zatím není.
- **Přesná GPS s RTK** (jen Middle a Max, `sprayDroneGps`, `#usageFactor` 0,85, 2 500 €): spotřeba l/ha o 15 % nižší (násobí `usageScale`), takže méně naplnění a přeletů. Rychlost se nemění. Údaj 15 % je herní zjednodušení, nikdo ho neměřil.
- **Relé tyč** (`objects/relay/relayPole.xml`, vehicle type `sdtRelayPole` = pallet + specializace `scripts/SprayDroneRelay.lua`, obchod 650 €, model `blender/build_link_items.py`): samostatný předmět z obchodu. Hráč ji nese v rukou, postaví vzpřímeně na zem a ovládá dvěma akcemi: **R rozloží / složí** (tři nohy stativu se rozevřou kolem pivotů `relayLeg1..3`, teleskopický stožár `relayMast` vyjede o 0,6 m, 3 s, `SprayDroneRelay.applyProgress`) a **B zapne / vypne** (`SDT_TOGGLE_FOOT`; zelená kontrolka `relayLed`, jen rozložená). Bez baterie: zapnutá běží bez omezení. Složená, vypnutá, převrácená nebo držená tyč dosah nezvětšuje. Stav (`unfolded`, `powered`) se ukládá do savegame a jde po síti stavem vozidla (dirty flag), příkazy klienta posílá `SprayDroneRelayEvent`. Dosah vleku se prodlouží o vzdálenost aktivního relé od vleku, když je relé v dosahu rádia vleku (`SprayDroneLink.getRangeBonus`, volá `updateRange`). Zjednodušení: kruh o poloměru dosah + vzdálenost relé kolem vleku, ne sjednocení dvou kruhů. Tyč stojí jako dynamický pallet na široké patě; stabilita na svahu neověřena.
- **Tablet** (`objects/tablet/droneTablet.xml`, pallet, obchod 400 €): hráč ho drží v rukou a levé tlačítko (`ACTIVATE_HANDTOOL`, jako vanilla ruční nástroje) otevře plánovač (`SprayDronePlannerScreen.show(vehicle, true)`) nejbližšího rozloženého vleku v dosahu rádia vleku nebo aktivního spojeného relé (`SprayDroneLink.findTrailers`). Bez spojení zobrazí `NO CONNECTION`; při odchodu ze signálu se plánovač zavře se stejnou hláškou (`getIsVehicleUsable`). Příkazy jdou přes stávající eventy (adresují vlek přes network id, nepotřebují nástup). Modul `scripts/SprayDroneLink.lua` se načítá z `modDesc` (`extraSourceFiles`, `addModEventListener`). Stránka v InGameMenu se nedělala (riziko).
- Neověřeno: aktivace E/LMB u tyče a E při držení tabletu, sklopení nohou (osy a úhly spočítal Blender, sklopení ve hře neviděl nikdo), stabilita stojící tyče (dynamický pallet), plánovač bez nástupu (`refreshRoutePreview`, `changeSetting`), obchod (kategorie `pallets`). Test: `python tmp/f/test_link.py`.


## Vápnění: mlýnkový vozík a nádobka na vápno (2026-10-18; přestavba nádobky a hadice 2026-10-21, viz „Přestavba 2026-10-21“ na konci sekce)

Dron umí vápnit. Vápno je jen další koncentrát a další přípravek v mixéru: `SDT_FINE_LIME` (Jemně mleté vápno, `xml/fillTypes.xml`, 1,1 kg/l,
ikona `hud/fillTypes/hud_fill_sdtFineLime.dds`) se v `<mixer>` Maxu mapuje `<ratio fillType="SDT_FINE_LIME" product="lime" concentrate="0.20"/>`
na vanilla `LIME` (sprayType LIME, `litersPerSecond` 0,09 → při `usageScale` 0,2 asi **648 l/ha**, 1 l vápna dá 5 l přípravku, tedy asi 130 l vápna na hektar).
Podíl 0,20 a spotřeba jsou odhad, doladit po zkoušce. Dron nese `LIME`, `flushSpray` zapisuje přes `FSDensityMapUtil.updateSprayArea` (vanilla `LIME_LEVEL`
jen se zapnutým `limeRequired` a jen na holé půdě, strništi, čerstvě zaseté nebo přerostlé plodině; zakázky na vápnění hra nemá).

**Max, vápenná konfigurace** (od 2026-10-21 zrušená, nádobka je v každém Maxu; text níž je historie): fill unit 3 má 350 l a přijímá i `SDT_FINE_LIME`,
hlavní nádrž (fill unit 1) přijímá navíc `lime`. Místo běžné indukční nádobky (skupina `inductionStd`) je větší bílá nádobka s hadicovou spojkou Storz
(`inductionLime`, `limeInletNode` = čelo spojky; `concentrateNeckNode` se konfigurací přesouvá nahoru na její hrdlo, `translationActive`). Kolize
`colInductionTank` a `concentrateFillRootNode` mají obálku větší nádobky ve všech konfiguracích (žádný kvádr navíc). Konfigurace přepínají všechny objekty jen
přes `...Active` (bez `...Inactive`), aby se sdílené uzly neprali. Max má vždy **zadní kulový věšák** (`rearHitchJoint`, `attacherJoints`, jointType `trailer`,
nový vehicleType `sprayDroneTrailerTow` = `sprayDroneTrailer` + `attacherJoints`); za něj jde zapřáhnout vozík. Ve Station: `<sprayDrone><limeInlet node fillUnitIndex fillType/>`,
`SprayDroneStation.getLimeInlet(vlek)` vrací vstup jen když vybraná konfigurace přijímá `SDT_FINE_LIME`.

**Mlýnkový vozík** `vehicles/sdtLimeMill` (storeItem, kategorie vleky BZUK, 16 500 €, vehicleType `sdtLimeMill` se spec `sprayDroneMill`,
`scripts/SprayDroneMill.lua`): jednonápravový vlek (oj tvaru A s kulovou spojkou, podpěrné kolečko, pneu 280/70 R15 jako Mini) s velkou nádobou na hrubé vápno,
šnekem, kladivovým mlýnem, dieselovým motorem s nádrží a cyklónovou nádobkou na jemné vápno. Fill units: **1** hrubé vápno (`lime`, 2 400 l,
`exactFillRootNode`: vanilla návěs / big bag se vyklopí do nádoby), **2** nafta (40 l, `dieselFillRootNode`; kanystr z modu nakloněný nad hrdlem `millDieselNeck`
nalévá jako u centrály Maxu), **3** jemné vápno (150 l mezisklad). Parametry v `<sprayDroneMill>`: `millRate` 6 l/s, `dieselPerHour` 6, `hoseLength` 9,5 m,
`hoseRate` 8 l/s, `pourRate` 4 l/s.

- Motor zapíná a vypíná hráč u vozíku (activatable, ACTIVATE_OBJECT u `millSoundNode`, dosah 3,2 m). Za chodu server po tikách přesouvá litry 1 → 3 (`millRate`),
  odebírá naftu a hlásí stav klientům (dirty flag: motor, mletí, čerpání, cíl hadice). Bez nafty se motor vypne.
- **Hadice** (activatable u portu `millHoseNozzle`, dosah 2,4 m): „Připojit hadici k nádobce na vápno“ najde nejbližší vlek se vstupem `limeInlet` do 90 % délky hadice
  (`SprayDroneMill.findTarget`), příkaz jde eventem `SprayDroneMillEvent` na server. Hadice se vykreslí řetězem článků `millHoseSeg1..72` (prověšená Bézierova křivka, články
  se natahují po ose Z jako u `layoutHose`), koncovka `millHoseEnd` sedí na čele vstupu a uložená hadice (`millHoseStored`: cívka pod nádobou + slepá spojka) se skryje.
  Čerpadlo (jen za chodu motoru) tlačí `SDT_FINE_LIME` z fill unit 3 do fill unit vstupu; nejde do nádobky s jiným druhem. Přes dosah hadice se sama odpojí.
- Vozík visí na zadním věšáku Maxu, nebo na jiném tahači (`trailerCar` / `trailerLow` / `trailer`); podpěrné kolečko se po zapřažení zvedá (animace `moveSupport`).

Blender: `blender/sdt_mlyn.py` (vozík), `sdt_lime.py` (nádobka a věšák Maxu), `build_trailer_mill.py` (uzly, kolize, kola, články hadice, DirtUV), `export_mill_mod.py`,
`headless_mill.py -- build | render | compose | export` (render a compose dělají náhledy do `tmp/vapneni/modely`). Max se sestavuje a exportuje jako dřív
(`headless_max.py -- build export`). Vozík nemá vmask (materiály na `default_vmask`), polepy a nápisy zatím chybí.

Ve hře neověřeno, na co si dát pozor: zapřažení vozíku za Max (jointType `trailer` a výška koule 0,58 m), nalévání nafty z kanystru do vozíku, vykreslení hadice při jízdě,
výchozí stav `limeRequired`, a že `exactFillRootNode` v nádobě přijme vápno z vanilla návěsu. Mimo rozsah zůstává pytlování (pytle jemného vápna), Mini / Middle a Precision Farming.

**Herní test vápnění (2026-10-18):** Max s konfigurací `TANK6000_LIME` + vozík zapřažený za zadní věšák drží rovně; motor, mletí (6 l/s), připojení hadice a čerpání do fill unit 3 Maxu (8 l/s) fungují, hadice se vykreslí od portu vozíku ke Storz vstupu nádobky. Neověřeno: aktivace klávesou R při chůzi (debug `view` vynutí letový režim a aktivace se pak nevybere; ovládání jde přes debug příkazy `millOn/millOff/millHose/millUnhose/millStatus`), míchání vápna v dronu a zápis `LIME_LEVEL` na pole. `prepare_testsave.py`: `--lime --mill --mill-lime --mill-diesel --player-at-mill`; pozice pickupu dát jako `--at=x,y,z,yaw` (se znaménkem mínus bez `=` argparse selže) a výška 60.5, jinak vozidla propadnou terénem (terén tam je 58,9 m).

**Přestavba 2026-10-21 (nádobka s kohoutem pro Max i Middle, nová hadice):** podle rešerše `docs/RESERSE-hadice.md`.
- **Žádná vápenná konfigurace v obchodě.** Max má jedinou nádobku (bývalá „vápenná“, `inductionLime`, 350 l pro obě velikosti nádrže), běžná `inductionStd` zůstává v Blenderu jen
  kvůli polepům a export ji skrývá. `concentrateNeckNode` stojí napevno na hrdle nové nádobky. Fill unit 3 přijímá oba koncentráty i `SDT_FINE_LIME`, v mixéru je poměr 0,20
  a `<limeInlet>` je vždy. Konfigurace `*_LIME` a texty `sdt_fillCfg_lime*` jsou pryč (`prepare_testsave.py` nemá `--lime`).
- **Middle** má totéž na své indukční nádobce (`build_induction_tank(hose_inlet=True)`): Storz/kamlok vstup s kohoutem na pravém boku (-X, vedle stupnice, o 0,10 m dozadu),
  uzly `limeInletNode` a `limeValveLever`; fill unit 3 přijímá `SDT_FINE_LIME` (kapacita zůstává podle velikosti nádrže, 40–250 l), v mixéru je `SDT_FINE_LIME` 0,20 a `<limeInlet>`.
- **Kohout spojky:** páka `limeValveLever` (otočný uzel na ose vřetene, `sdt_tanks.valve_lever_node`; páka stojí v zavřené poloze napříč tokem). Po připojení hadice je kohout
  zavřený; ventil se otevře sám při připojení hadice (dřív levé tlačítko myši, `SprayDroneMill.CMD_VALVE`), R hadici odpojí. Čerpá se jen při připojené hadici, otevřeném kohoutu a běžícím motoru mlýnu.
  Stav `valveOpen` jde klientům stavem vozíku, páku otáčí `SprayDroneMill.updateValve` podle `<limeInlet valveNode valveOpenAngle>`.
- **Nová hadice mlýnku** (`hoseCurve` v `SprayDroneMill.lua`): pevná délka `hoseLength` (z cívky se odvine jen vzdálenost konců + 12 % + 0,9 m, nejvýš celá), rovný nájezd 0,18 m u
  portu i koncovky, tečny ve směru portu a vstupu jako řídicí body Béziera, rezerva délky se vybere půlením průvěsu a postranního ohybu. Body leží nejníž na podlaze: terén, statický
  objekt, budova nebo silnice do 0,6 m nad terénem (paprsek shora, mřížka 0,5 m s platností 1,5 s). Články se přesahují na obou stranách ohybu. Starý tvar (svislý stoupák, zlomy u země) je pryč.
  Hadice k dronu (`SprayDroneService`) se nezměnila: už má pevnou délku, přívod do hrdla a Bézierův průvěs.
- **Ukládání:** mlýnek ukládá hadici (`#hoseTarget` = uniqueId vleku) a kohout; po načtení hry si vlek hledá až 15 s. Motor po načtení stojí.
- Neověřeno ve hře: viz konec sekce (herní test 2026-10-21).

**Ovládání vozíku (2026-10-18, ověřeno ve hře přes ladicí příkazy a kliknutí):** vozík se rozkládá X (hadice pod násypkou zmizí a smotaná leží na zemi u portu), motor zapíná B pěšky u rozvaděče (akce `SDT_TOGGLE_FOOT`) nebo levé tlačítko na tlačítku rozvaděče, ve vozíku B (`IMPLEMENT_EXTRA`). Hadici u volného konce chytí levé tlačítko myši nebo R, druhé kliknutí ji pustí (vrátí se do smotku); připojit jde jen když hráč stojí do 1,4 m vodorovně od vstupu nádobky (vstup je ve výšce ~1,7 m, měří se od výšky hrudi ±1 m). Tvar hadice: z portu obloukem k zemi, po zemi s lehkým klikatěním (míň, čím je napnutější), u cíle kolmo vzhůru a čtvrtkruhový ohyb do koncovky (`groundedCurve` v `SprayDroneMill.lua`). Vanilla má jen `ConnectionHoses` mezi zapřaženými stroji (pevná délka, žádné tahání hráčem), proto vlastní systém.

## Pumpa se sací hadicí a mlýnek bez hadice (2026-10-21; ve hře ověřeno na Maxu, Middle jen načtení)

Hadice mlýnku (cívka, připojení u vstupu nádobky, foldable) je **zrušená**. Mlýnek má jen výstup jemného vápna (spojka Storz, uzel `millOutletPort`,
slepá spojka `millPortCap` zmizí, když je připojená hadice) a motor (B pěšky `SDT_TOGGLE_FOOT`, ve vozíku `IMPLEMENT_EXTRA`). Hadici má **vlek** (Max, Middle): scripts/SprayDroneWaterHose.lua.

- **Napojovací body vleku:** ventily vodních nádrží (`<sprayDroneWaterHose><ports>`, empty `waterHosePort<velikost>[B]` pod skupinou nádrže, nepoužité nádrže jsou
  skryté s nádrží) a vstup nádobky na koncentrát (`<limeInlet>`, s kohoutem a pákou).
- **Ovládání:** R u ventilu / vstupu vezme konec hadice, R u zdroje ho připojí, R u ventilu nebo zdroje ji odpojí. U vstupu na koncentrát otevírá / zavírá kohout levé
  tlačítko myši (páka `limeValveLever`).
- **Zdroje:** ke ventilu vody libovolné vozidlo s vodou (IBC, cisterna, vodní vlek; konec hadice se připojí na karoserii u ruky); ke vstupu na koncentrát výstup
  mlýnku s jemným vápnem (mlýn musí běžet, kohout otevřený). Průtok vody 12 l/s, vápna nejvýš `hoseRate` mlýnku (8 l/s). Nádrž s jiným přípravkem hlásí `sdt_wh_mixed`.
- **Geometrie:** sdílená knihovna scripts/SprayDroneHoseLib.lua (obcházení vozidel podle `v.size`, ležení na terénu / statických objektech, stoupání ke koncům,
  koncovka míří dopředu od hráče, výška konce podle náklonu kamery). Délka hadice 12 m.
- **Stav:** vytažení, nesený konec, zdroj a kohout jdou ve stavu vozidla (MP), připojení se ukládá do savu (zdroj podle uniqueId). Přenosná pumpa (níž) vodu z IBC, cisterny a rybníka přečerpává vlastními hadicemi; placeable zdroje zatím nejsou.
- **Ladění** (`SprayDroneDebug.ENABLED`): `spawnIbc` (IBC z LSFM Universal Tank Pack s vodou), `spawnMiddle`, `whStatus`, `millFill`, `millOn`, `millFloor`.

## Přenosná pumpa na vodu (2026-10-22, jeden vstup s přepínáním 2026-10-23; Lua, XML a model hotové, přepínání vstupu ve hře neověřeno, dřív ověřeno simulací hráče přes debug příkazy, ruční ovládání R a multiplayer neověřeny)

Samostatný objekt typu `pallet` (`objects/pump/waterPump.xml`, vehicle type `sdtWaterPump`, scripts/SprayDronePump.lua + SprayDroneWaterHose.lua), prodává se v kategorii BZUK / vybavení.
Naftový motor žene čerpadlo se **dvěma popsanými spojkami** (cedulky VSTUP / VÝSTUP, barevné objímky modrá / červená) a **dvěma vlastními tažnými hadicemi**;
pevné sání s košem už není, pumpu jde postavit kamkoli a hadice se vedou, kam je třeba.

- **VSTUP (modrý, +X) má dva režimy, přepíná se ručně** (žádná automatika, výchozí je „nádrž“). Hadice je jedna (10 m, 60 článků, `inHoseSeg*`), mění se její koncovka a to, co se s ní dělá:
  - **nádrž:** konec hadice je spojka Storz (`inHoseEnd`), hráč ji napojí na výstup IBC / cisterny / vodního vleku (viz „Výstup zdroje“ níž); čerpá se jen po napojení. Za chodu motoru plní těleso
    pumpy (fill unit 2, 200 l, 16 l/s) a zdroj se opravdu vyprazdňuje.
  - **rybník:** konec hadice je sací koš (`inStrainerEnd`, rychlospojka + mosazný nátrubek + koš s červeným ventilem); hráč ho odnese k vodě a R ho položí na dno pod hladinu (hloubka ≥ `minDepth`
    0,15 m, paprsek `CollisionFlag.WATER`), nic se nenapojuje. Bod ve světových souřadnicích se ukládá do savu, server každých 500 ms kontroluje, jestli koš pořád stojí ve vodě; za chodu motoru plní těleso 16 l/s.
  - **Přepnutí:** levé tlačítko myši u vstupní spojky (do 1,9 m; text „Vstup na rybník (sací koš)“ / „Vstup na nádrž (spojka Storz)“), stejná interakce jako přepnutí výstupu mlýnku
    (`SprayDroneMill.isModeClickBlocked` je sdílená pojistka: X a předmět v rukou se nepřepíná). Spojka patří hadici, proto klik zpracuje `SprayDroneWaterHoseActivatable` (R tam dál bere / odpojuje hadici)
    a volá `SprayDronePump.toggleMode`. Jde jen se **stojícím motorem** a když sací hadice **není napojená** ke zdroji (odložená nebo nesená nevadí; nesená se při přepnutí odloží); jinak blikající hláška
    `sdt_pump_modeEngineOn` / `sdt_pump_modeHoseAttached` (`SprayDronePump.getModeBlocker`, server ho kontroluje znovu).
  - **Stav:** `spec.pondMode` v `SprayDronePump`, příkaz `CMD_MODE_TOGGLE` přes `SprayDronePumpEvent`, režim je ve stavu vozidla (`writeState` / `readState`, tedy i pro klienta po připojení) a v savegame
    `…sprayDronePump#pondMode` (jen když je rybník). Druh spojky `inlet` v XML (`<port kind="inlet"/>`) se v `SprayDroneWaterHose.getPorts` podle režimu změní na `water` nebo `pond`, koncovku volí `selectEnd`
    (`hoseEnd` + `strainerEnd` v XML hadice). Záznam akcí: `SDT akce` „vstup přepnut na …“ / „přepnutí vstupu odmítnuto“.
  - **Stará savegame:** hadice na zrušeném rybníkovém vstupu (dřív druhá hadice) se nenačte (připojení nesouhlasí s druhem spojky se zahodí v `resolvePending`), stará výstupní hadice, která byla třetí,
    se taky nenačte a je odložená; vstupní hadice napojená na IBC se načte v režimu nádrž. Pumpa uložená na vlek režim neuchová (po vyndání je v režimu nádrž).
- **VÝSTUP (červený, −X):** hadice 12 m z pumpy na vodní ventil velkého vleku (`findSinkAt`, konec do 1,0 m od ventilu, ventil nesmí být obsazený vlastní hadicí vleku nebo jinou výstupní hadicí).
  Za chodu motoru plní nádrž vleku z tělesa pumpy (16 l/s); jiný přípravek v nádrži vleku zablokuje přelévání (hláška `sdt_wh_mixed`). Z pumpy se voda jinak odebírat nedá
  (`getWaterUnit` vrací pro pumpu nil), vlastní hadice vleku k pumpě nejde.
- **Ovládání:** B (`SDT_TOGGLE_FOOT`) u pumpy zapne / vypne motor. R u spojky vezme hadici (text podle spojky), R u ventilu / zdroje / vody ji připojí, R u spojky nebo u druhého konce odpojí. Pumpa
  bez toku (nic nepřelévá) po 1,5 s ukáže varování. Nafta (fill unit 1, 15 l, 3 l/h) se nalévá z kanystru nad hrdlo (`pumpDieselNeck`) jako u mlýnku (`SprayDroneMill.updatePour`).
- **Systém hadic:** `SprayDroneWaterHose` má na vozidle seznam hadic (`spec.hoses`, XML `<hoses><hose …><port node kind/>`, vlek má jednu jako dřív přes `<ports>`); každá hadice má vlastní řetěz článků,
  koncovku, stav a číslo v příkazu / eventu (`HOSE_BITS` 2). Druhy spojek: `water` (zdroj s vodou, vlek: ventil), `pond` (hladina), `inlet` (vstup pumpy, podle režimu water / pond), `sink` (ventil vleku), `lime` (vstup nádobky).
- **Stav:** motor, „čerpá se“ (`flowing`, `markFlow`) a režim vstupu jdou ve stavu vozidla, hadice (včetně rybníka) ve stavu `SprayDroneWaterHose` (MP); motor se po načtení hry nespouští, hladiny ukládá FillUnit.
- **Výstup zdroje pro každou vodní hadici** (i vlekovou): zdroj s nízkým vypouštěcím uzlem (`spec_dischargeable.dischargeNodes`, v i3d do 0,8 m nad počátkem vozidla; LSFM IBC, abi 550 / 1600, LSFM tank
  trailery) se napojí na ten uzel, zdroj s uzlem nahoře (kupole) nebo bez uzlu (vanilla IBC, Lizard Self Made Water Tank) na bok při zemi. Bod se vždy upřesní vodorovným paprskem
  (`SURFACE_MASK` VEHICLE + DYNAMIC_OBJECT + DEFAULT + TRAILER, výška podle uzlu / podlahy) na skutečný povrch zdroje, takže koncovka sedí na karoserii a netrčí ve vzduchu; za nárazníkem (uzel mimo
  karoserii) se použije nejbližší povrch u uzlu. Ve hře ověřeno na pěti zdrojích a třech natočeních (550, 1600, LSFM 2500 L a 7500 L, Lizard IBC).
- **Uložení na vlek (Max, Middle; 2026-10-22):** pumpa se dá uložit na vlek a zase vyndat (`scripts/SprayDronePumpSlots.lua`, `events/SprayDronePumpSlotEvent.lua`, princip jako držáky relé tyčí;
  sdílí její pomocné funkce a výpočet místa vyndání). Nafta (fill unit 1, 15 l) a zapínání motoru (B u pumpy) zůstávají na pumpě, na vleku se ukládá jen stav nafty a farma.
  R u slotu (do 2,5 m): s pumpou v rukou nebo ležící do 2,5 m **uložit** (vypnutý motor; hadice pumpy se odloží; maketa se nenačítá, voda v tělese se vynuluje), jinak **vyndat** (nová pumpa
  s uloženou naftou na zemi u hráče, dál od vleku; do rukou ji hráč zvedne sám, 60 kg). Uložená pumpa neběží a nepálí naftu. Slot (jeden na vlek) se ukládá do savegame
  (`…sprayDroneStation.pumpSlot#diesel`, `#farmId`) a jde klientům ve stavu vleku. V XML vleku `<sprayDrone><pumpSlot node translation rotation visible/>`: bod v prostoru existujícího uzlu,
  Max `0 1.0 2.2` a Middle `0 0.9 2.3` v kořeni komponenty (nad ojí, u čela rámu, kde nic nestojí a hráč se tam dostane ze země). Paluba nemá volné místo na 0,9 × 1,1 × 0,8 m a nový export i3d se nedělal,
  proto `visible="false"` (jen chování; `visible="true"` načte za běhu vizuální uzel z pumpového i3d na uzel slotu, **neověřeno**). Texty `sdt_pumpslot_*`, řádky SDT děj z watcheru.
  Ve hře ověřeno ladicími příkazy: uložení, vyndání, přenos Max → země → Middle → země, nafta 9 l přežije uložení hry i načtení. Ruční R, multiplayer a viditelnou maketu nikdo neověřil.
- **Ladění:** `spawnPump`, `pumpOn`, `pumpOff`, `pumpModeTank`, `pumpModePond`, `pumpStatus`, `pumpToTrailer`, `pumpToIbc`, `pumpView1..4`, `pumpStore`, `pumpTake`, `pumpFuel`, `pumpSlotInfo`, `removeMiddle`; scény `station2` (pumpa + IBC + cisterna u vleku), `pondSetup`
  (pumpa na břehu a vlek podél něj, čísla v `debug.xml#view` přes `sdt_debug.ps1 -Raw`), `cistern` (jedna z `SprayDroneDebug.CISTERNS`), `shoreScan`, `waterMap`, `worldView`; simulace hráče `whConnect<N>`
  (první hadice vozidla, u pumpy přepne vstup na nádrž a napojí ho), `whPond` (přepne vstup na rybník a položí koš), `whOut`, `whValve`, `whDrop`, `whStatus`; `pondSetup` nastaví pumpu do režimu rybník,
  `station2` do režimu nádrž.
- **Ve hře neověřeno (přepínání vstupu):** levé tlačítko u vstupní spojky přepne režim a změní se koncovka hadice; hláška při běžícím motoru a při napojené hadici; v režimu rybník sací koš do vody
  a čerpání; v režimu nádrž napojení na IBC; přepnutí nesené hadice; uložení a načtení hry v obou režimech; multiplayer (klient přepne, druhý klient po připojení vidí režim a koncovku); stará savegame.

### Big bag z mlýnku: ventil a výsypná roura (2026-10-29 podle `docs/NAVRH-mlyn-plneni-bigbagu.md`; Lua, XML a modely hotové, ve hře neověřeno)

Workflow: hrubé vápno (vanilla big bag / vlek, `exactFillRootNode` mlýnku) -> mlýnek -> a) hadice do vleku (pumpa vleku, `SprayDroneWaterHose`), nebo b) **stojící big bag
s jemným vápnem** pod výsypnou rourou, který se pak vozí a položí na výsypnou stolici násypky. Nahradilo foukací rouru na spojce (`blowPipe.i3d`, `build_blowpipe.py` v `blender/archiv`).
- **Ventil (rozdělovač)** pod nádobkou jemného vápna (`sdt_mlyn.build_spout`, `VALVE_C`): klapka na trubce ke spojce Storz, odbočka dozadu do potrubí po palubě. Páka (`millValveLever`,
  animace `valveLever` 0,6 s): **vodorovně ven = hadice, svisle nahoru = roura**. Přepíná se pěšky levým tlačítkem na páku (`SprayDroneMillModeActivatable`, do 2,6 m od páky), ve vozíku
  / z tahače **Y** (`IMPLEMENT_EXTRA3`); příkaz `CMD_VALVE_TOGGLE`, stav `valveSpout` (stav vozidla, savegame `…sprayDroneMill#valveSpout`). Jde přepnout i s připojenou hadicí: hadice zůstane,
  `getOutlet` vrací `closed = true` a `SprayDroneWaterHose` nic nepřeleje; hráč nastoupený nebo do 12 m vidí nápovědu „Výstup mlýnku je přepnutý na rouru, hadice nic nedostane“
  (`sdt_mill_hoseSpout`, `addExtraPrintText`). Slepá spojka je vidět, dokud na spojce není hadice.
- **Výsypná roura:** potrubí DN 100 po palubě (x −0,67, tři objímky) do stoupačky v pravém zadním rohu (i3d −1,03; z −2,26), ložisko otočného kloubu (y 1,46), vodorovné rameno 0,80 m
  v ose y 1,62, na konci spádová trubka dolů a koleno s plnicí hlavou **z boku vaku** (ústí vodorovně od kloubu, osa 1,02 m, pod horní hranou látky; změna 2026-10-29 na Pavlův pokyn, aby hlavu vak z většiny zakryl a plný vak šel odvézt), opěrka ramene na boku násypky. Rameno se otáčí kolem svislé osy (`millSpoutPivot`,
  animace `spoutSwing` 6 s, `0 → −180°`): **1 přeprava** (čas 0, rameno dopředu podél násypky), **2 vedle vozíku** (0,5, vpravo; vak 0,33 m od kola), **3 za vozíkem** (1; vak 0,29 m
  od zádě). Ovládání **O** (`TOGGLE_PIPE`, cyklus 1 → 2 → 3 → 1, texty `sdt_mill_spoutSide / Rear / Fold`) ve vozíku / z tahače, pěšky levé tlačítko na kloub (`millSpoutJoint`,
  `SprayDroneMillSpoutActivatable`, do 2,8 m). Vanilla `Pipe` se nepoužívá (chce `Dischargeable` a nastartovaný tahač). Příkazy `CMD_SPOUT_TRANSPORT + stav − 1` (4–6, `CMD_BITS` 3),
  stav `spoutState` (2 bity ve stavu vozidla, savegame `…#spoutState`). Animace dojíždí na serveru i klientech sama podle stavu (`driveAnimation`, bez událostí animace; po načtení skočí).
- **Kam teče** (`SprayDroneMill.getFlowTarget`, test `tools/test_mill_flow.py`): motor běží a ventil na hadici -> hadice; ventil na rouře, roura vyklopená (2 / 3), dotočená a vozík
  stojí (< 1 km/h) -> vak; roura složená -> nic, za chodu motoru bliká „Výsypná roura je složená – vyklop ji (O)“ (`sdt_mill_spoutFolded`, jen nastoupenému / do 12 m). Mezisklad
  (150 l) se plní dál, dokud není plný.
- **Vak u hlavy:** hlava stojí z boku vaku na straně k vozíku, střed vaku je o `neckOffset` 0,50 m dál od kloubu (8 cm mezera + polovina hloubky vaku 0,42 m); nic z roury nesahá nad půdorys vaku, takže plný vak jde zvednout za poutka a odvézt od vozíku (`tools/test_mill_flow.py`, sweep v Blenderu `out/mill_build_check/side_check.py`, náhledy `tmp/mill_side/`). Server každých 250 ms hledá
  (`findBag`) vozidlo s prvním fill unitem pro `SDT_FINE_LIME` a místem, s kořenem do `halfWidth` 0,6 m od očekávaného středu (`getBagSpot`) a 0,8–2,5 m pod hlavou; když tam
  nestojí žádný (ani plný / cizí), postaví nový prázdný (`spawnBag`: kořen na zem, hloubkou 0,84 m podél ramene). `<bagOutput head pivot neck neckOffset
  halfWidth depth>` v `sdtLimeMill.xml`. Sype `hoseRate` 8 l/s, hrdlo vaku `millBagNeck` a prach (`dust.blowing` na `millFillHead`) jsou vidět jen za sypání (`valveSpout` a `pumping`).
  Záznam: `SDT akce` při přepnutí ventilu / roury, `SDT děj: mlýnek …: sypání do big bagu začalo / skončilo, nasypáno X l`.
- **Hladina hrubého vápna:** vanilla `fillPlane` fill unitu 1 (rovina `coarseFillPlane` 1,72 × 1,56 m v ose násypky, klíče y 1,00 → 2,50 s měřítkem podle šikmých stěn).
- **Big bag** `objects/limeBigBag/limeBigBag.xml`: vanilla `bigBag` (FIBC vak s poutkem bez stojanu) přes `<parentFile>`, `SDT_FINE_LIME`, 1 000 l, `fillTypeMaterials` `material(3)` = lime,
  kupuje se prázdný (225 €, kategorie `bigbagPallets`); sype vanilla `dischargeable` (`emptySpeed` beze změny) do nádoby s `exactFillRootNode`, která jemné vápno přijímá (stolice násypky).
- Ladění: `millValve` (přepnout ventil), `millModeBag` / `millModeHose` (ventil na rouru / hadici), `millSpout` (další stav roury), `millBagInfo` (ventil, roura, animace, tok a důvod,
  hlava nad zemí, střed vaku, vak, mezisklad, hadice, hrdlo), `spawnLimeBigBag`, `spawnLimeBigBagFull` (300 l, pod hlavu), `bagStatus`, `millFill`, `millOn`.
- **Ověřit ve hře:** O ve vozíku i z tahače (text podle stavu, 3 polohy, zvuky), klik na kloub a na páku, Y; vak se postaví pod hlavu v poloze 2 i 3 a hlava nesedí v poutku; tok jen
  s dotočenou rourou a stojícím vozíkem; hláška složené roury; hadice připojená při ventilu na rouře nic nedostane a ukáže nápovědu; hladina v násypce; savegame (ventil, roura);
  multiplayer (klient přepíná, nově připojený vidí polohy). Náhledy exportu: `out/mill_build_check/mill_*.png`.

#### Prach při mletí (2026-10-23; Lua, XML, efekt a uzel hotové, ve hře neověřeno)

Za chodu mlýna se z mlýnku práší, jen jako vizuál na klientech (v multiplayeru se nic neposílá navíc, řídí ho už synchronizovaný stav `milling`, `pumping`, `valveSpout`).
- **Efekt** `effects/millDust.i3d` (generuje `python blender/build_mill_dust.py`, bez Blenderu; stejná technika jako mlha postřiku: ručně psané `Dynamics`, emitor z i3dConverteru, kouřový atlas `smoke6x6`
  na vanilla `psSubUVShader`, bílošedý tón). Dva systémy: `millDustIn` (světlý prach, ~10 částic/s, 1,8 s, stoupá cca 0,6 m) a `millDustOut` (~14 částic/s, 2,2 s, klesá od ústí a rozpíná se).
  Načtení přes `SprayDroneStation.loadSprayMist` (`ParticleUtil.loadParticleSystemFromNode`), `<dust><milling>/<blowing><effectNode …/></dust>` v `sdtLimeMill.xml`.
- **Vstup:** uzel `millDustIn` (nový prázdný uzel modelu, gumový límec výsypky šneku do mlýna, nad víkem mlýna); emitor míří dolů, skript ho otočí nahoru. Běží, dokud mlýn mele (`spec.milling`, stejná podmínka jako zvuk mletí).
- **Výstup:** jen když se do big bagu opravdu sype (`valveSpout` a `pumping`); emitor je na uzlu `millFillHead` (plnicí hlava výsypné roury). Hadicí a bez big bagu se nepráší.
- **Záznam:** `SDT děj: mlýnek …: prach u výsypky do mlýna / pod plnicí hlavou začal / skončil`.
- Poprašek na zemi se nedělá (vanilla pro něj nemá efekt bez zápisu do density map).
- Ověřit ve hře: viditelnost a množství prachu (má být „trochu“) zblízka i z dálky, směr nahoru u výsypky, plume u ústí roury a jeho dosah ke big bagu, prach zmizí po vypnutí motoru / odpojení big bagu, log bez `Particle System`.

### Násypka na jemné vápno (2026-10-22; Lua, XML a model hotové, ve hře ověřeno ladicími příkazy i klávesou B, multiplayer a ruční nošení neověřeny)

Workflow: pytle jemného vápna (`limeBag50`) nebo big bag (`limeBigBag`) položený na výsypnou stolici -> **násypka** -> hadice velkého vleku (vápnová spojka, port 5) -> koncentrátová nádobka vleku.
Přenosná jednotka jako pumpa (pallet, `supportsPickUp`, 120 kg, 2 400 €, kategorie BZUK vybavení), `objects/hopper/limeHopper.xml` (vehicle type `sdtLimeHopper` = `pallet` + `sprayDronePump` + `sprayDroneHopper`).
- **Model** `blender/build_hopper.py` (`blender.exe -b --python blender\build_hopper.py`, i3dMappings se přepíšou do XML): čtvercový trubkový rám 1,04 × 1,0 m, **lievec se stolicí uprostřed rámu**
  (2026-10-29: dřív stolice 0,14 m před středem rámu a motor za ní), ústí 0,8 × 0,8 m (žlutý okraj), pod ním podavač s dmychadlem s osou po X, na boku +X **zmenšený motor s nádrží** (`build_pump.build_engine` / `build_tank`
  na 72 %, otočené o −90° čelem příruby k podavači, nádrž nad motorem pod šikmou stěnou lievce), výstupní spojka Storz na boku −X. Uzly: `hopperSoundNode` (ovládání motoru), `hopperDieselNeck`, `hopperFunnel` (střed ústí), `hopperOutletPort`;
  kolize pod lievcem, stolice a patky opěr; `limeFillRootNode` (plochý kvádr pod mřížkou) a `dieselFillRootNode` (kolem nádrže) jsou `exactFillRootNode`. Skript spočte těžiště z odhadu hmotností dílů (`MASSES`)
  a zapíše ho s rozměry kolizí do `blender/limeHopper_geometry.json` (souřadnice hry), z něj `tools/test_hopper.py` hlídá `centerOfMass` v XML a kolize patek.
- **Fill units:** 1 nafta (15 l, nalévá se z kanystru jako u pumpy), 2 jemné vápno `SDT_FINE_LIME` (**400 l** = lievec ~150 l + nástavec do 1,33 m; plní se bez motoru).
- **Výsypná stolice (2026-10-29, `NAVRH-mlyn-plneni-bigbagu.md` kap. 4, ve hře neověřeno):** nástavec 0,9 × 0,9 m nad ústím lievce do y 1,40, dosedací rám z jeklu, rohová vodítka
  (vak 0,99 × 0,84 m sjede na střed), mřížka a nízký nůž (dvě zkřížené čepele 0,34 m, špička 0,04 m nad rámem). Vak se nakladačem jen **položí** na rám (kolize `stoolFloor` přes celý otvor, `stoolRail*`, `stoolGuide*`; kolize vanilla vaku jsou jen čtyři kvádry kolem středu, které se s ubývající náplní stahují, bez podlahy by částečně plný vak propadl do nástavce)
  a jeho vanilla `Dischargeable` sám sype do `limeFillRootNode` pod mřížkou; když je zásoba plná, stojí, a jak hadice ubírá, pokračuje. `hopperFunnel` (pytle) je na rámu stolice.
  Hladina zásoby: vanilla `fillPlane` (`limeFillPlane` 0,9 × 0,9 m, klíče y 0,48 → 1,33).
- **Vysouvací opěry do kříže** (`<legs travel="0.30" drop="0.06" duration="2">`, uzly `hopperLeg1..4` + patky `hopperFoot1..4` + kolize `hopperFootCol1..4`): pěšky levé tlačítko u kterékoli patky
  (`SprayDroneHopperLegsActivatable`, do 1,8 m, `sdt_hopper_legsOut / legsIn`), event `SprayDroneHopperEvent`, stav `legsOut` (stav vozidla, savegame `…sprayDroneHopper#legsOut`).
  Rameno se vysouvá ze šikmého pouzdra v rohu rámu po své ose x (uzel je natočený o 45°, `SprayDroneHopper.getLegDirection` vezme osu ramene a otočí ji ven od středu) o 0,30 m,
  patky pak stojí v rozích čtverce ~1,7 × 1,7 m; pak vizuální patka klesne o 0,06 m (5 cm výšky zasunuté patky + 1 cm). Rameno v pouzdře zůstane 0,145 m.
  **Kolize patky** `hopperFootCol1..4` (kvádr 0,13 m, `compoundChild`, filtr jako rám `0x10000 / 0xfffdfbff`) stojí **pevně ve skupině `collisions` pod vysunutou patkou**,
  spodek **1 cm pod spodkem kolize rámu** (nejnižší bod kolizí; vizuální patka po poklesu sedí přesně na něm), a za běhu se **nikdy neposouvá** – mění se jen filtr:
  `SprayDroneHopper.updateFeetCollision` jí vrátí filtr z i3d, když jsou opěry celé venku (`getFeetCarry`: `legsOut` a poloha 1), a na začátku zasouvání nastaví `0 / 0`;
  při změně probudí tělo (`Vehicle:wakeUp`). Platí na serveru i klientech (stav ze streamu) a po načtení uložené hry hned. Vysunutá násypka tak stojí na čtyřech patkách
  (o 1 cm výš), zasunutou nese rám. Proč ne pohyblivá kolize: kolize jezdící s ramenem 2 cm nad zemí nenesla (Pavel 2026-10-29: „nejsou tam kolize a propadají se“),
  klesající se zabořila do terénu a shodila vak, a posouvání `compoundChild` tvarů se tluče s posunem o těžiště po přepnutí těla na kinematické (upnutí na vlek, viz
  `SprayDroneRelay.updateFreeze`). Na hrbolatém terénu (zem pod patkou výš než pod rámem) se násypka po zapnutí patek jednorázově nadzvedne/nakloní o ten rozdíl. Ladění: příkaz `hopperFeet`
  (výšky rámu, patek a kolizí nad terénem, filtr). Ve hře neověřeno. **Vak na stolici sype jen s vysunutými opěrami** (`getFillUnitSupportsToolType` odmítne
  `DISCHARGEABLE`), pytle jdou vždy. Opěry se vysouvají **před** položením vaku: s vakem na stolici (`findStoolBag`, i propadlým) nejdou vysunout ani zasunout
  (hláška `sdt_hopper_legsBag`) a hráč do 6 m vidí, že vak se zasunutými opěrami nesype (`sdt_hopper_bagLegsIn`).
  **Těžiště** (`centerOfMass` 0,052 0,473 0,009, spočtené): vak sedí v ose rámu, zbytek posunu dělá motor na boku. Testy `tools/test_hopper.py` (v `check_all.py`).
- **Motor** je stejná specializace jako u pumpy (`SprayDronePump`: nafta 3 l/h, B u motoru, zvuk, event `SprayDronePumpEvent`); v XML se liší jen popisky (`textStart` / `textStop` / `textNoFuel`, `sdt_hopper_*`), `logName`,
  `dryWarning="false"` (bez varování „pumpa nic nečerpá“) a `storable="false"` (násypku nejde uložit do držáku pumpy na vleku, `SprayDronePumpSlots.getPumpState`). Stojící předmět se uspí a přestane volat `onUpdate`,
  proto `SprayDronePumpWake` (posluchač modu v `SprayDronePump.lua`) drží pumpu a násypku vzhůru, dokud je do 20 m hráč.
- **Vstup:** a) **pytel** `limeBag50` naklopený víčkem dolů nad ústím se vysype rychlostí `pourRate` 8 l/s (`SprayDroneMill.updatePour` zobecněné o `pourUnit` / `pourNeck` / `pourKind` / `pourBelow`; víčko smí být do 0,5 m od uzlu
  `hopperFunnel` a až 0,35 m pod ním); b) **big bag** `limeBigBag` položený na stolici sype vanilla `Dischargeable` (raycast dolů, `getFillUnitSupportsFillType` cíle) do
  `limeFillRootNode` (jen s vysunutými opěrami, viz výš).
- **Výstup:** `SprayDroneHopper.getOutlet / isRunning / markPumping / markOutletUsed` jsou stejné rozhraní jako u mlýnku; `SprayDroneWaterHose` je volá přes `getLimeModule(vehicle)` (mlýnek nebo násypka). Hadice vleku se k výstupu připojí,
  když je v násypce vápno; vápno teče `hoseRate` 8 l/s jen za chodu motoru, při otevřeném kohoutu vleku a pokud je v nádobce místo.
- **Záznam:** `SDT akce: násypka id N: zapnutí / vypnutí motoru`, `SDT děj: … nalévání začalo / skončilo, přeléváno X l za Y s` (nově i u kanystru nafty do pumpy a mlýnku), tok hadicí jako u mlýnku.
- **Ladění** (`SprayDroneDebug.PLAY`): `spawnHopper` (3,5 m od vápnové spojky vleku výstupem k vleku, 10 l nafty), `hopperOn`, `hopperOff`, `hopperFill` (+200 l), `hopperDrain` (koncentrát vleku na 100 l), `hopperBag`
  (pytel 50 l víčkem dolů nad ústím, 14 s), `hopperBigBag` (big bag 300 l položený na stolici), `hopperLegs` (vysunout / zasunout opěry), `hopperInfo` (zásoba, hladina fillPlane,
  opěry, smí vak sypat, vaky do 3 m: poloha vůči rámu ok / vedle / propadl / nad a stav výpusti), obojí cílí na nejbližší násypku k hráči, `hopperDrop` (smazat pytle a big bagy), `hopperCam` (pohled, `view` v souřadnicích násypky), `hopperStatus`.
  Držené předměty se na dobu držení přepnou na kinematické (jinak je gravitace při spícím vleku sváděla dolů a sypání se zastavilo).
- **Ve hře ověřeno (slot 10, Max):** pytel 50 l se vsype za 6,2 s; big bag 300 l se vyklopí do lievce (včetně sečtení s pytlem, 350 l); motor jde zapnout klávesou B u motoru; hadice vleku port 5 se připojí k výstupu, po otevření kohoutu teče
  8 l/s (250 l za 31 s) do nádobky; tok se zastaví při vypnutém motoru, při plné nádobce (350 l, v násypce zůstane zbytek) a při prázdné násypce. Snímky `out/mod_build/nasypka_01…07b_*.png`.
- **Neověřeno:** multiplayer, ruční nošení násypky (zvednutí), skutečné naklopení pytle rukama (testovalo se držením objektu na místě), vyklopení big bagu vysokozdvižným vozíkem, uložení savegame se zapojenou hadicí,
  stolice (2026-10-29): vak položený nakladačem drží na rámu a sype jen s vysunutými opěrami, hladina stoupá, opěry (klik, pohyb, savegame, MP), stabilita s plným vakem;
  přestavba 2026-10-29 (stolice uprostřed, motor na boku, opěry do kříže s vodorovně jezdící kolizí patek): že posun kolize vnořené pod ramenem hra přenese do fyziky, že vysouvání na rovině
  násypkou nepohne, nalévání nafty z kanystru pod převisem lievce (hrdlo 0,36 m pod stěnou lievce).

### Záznam zvuků do logu (2026-10-22)

`SprayDroneSound.lua` obaluje `SoundManager:playSample` a `stopSample`: každé spuštění a zastavení vzorku, který patří vozidlu z modu (i zvuky z XML: animace, spojky tahače,
WaterTrailer, podvozek), se zapíše do log.txt jako `SDT zvuk: START|STOP|JEDNORÁZOVĚ <vzorek> [šablona, soubor] na <vozidlo> (id, uzel) – <důvod> | poslední akce: <akce, před N ms>`.
Smyčky se zapisují jen při změně, jednorázové zvuky při každém přehrání. Důvod předává skript přes `SprayDroneSound.because` (řídicí stav kanálu, `engineOn / milling / pumping` mlýnku,
otáčky rotoru), u kanálů vleku se navíc píše `ZAPNUTO / VYPNUTO` při změně řídicího stavu. „Poslední akce“ nastavuje `SprayDroneSound.noteAction` (zapnutí a vypnutí motoru mlýnku a pumpy,
příkazy vodní hadice, centrála, přečerpávání) a vypisuje se i jako samostatný řádek `SDT akce:`. Vypnutí: `SprayDroneSound.LOG = false`. Nezachytí zvuky GUI (planner) a vanilla zvuky cizích vozidel.

### Záznam akcí a změn stavu, průchod hrou (2026-10-22)

K `SDT akce` a `SDT zvuk` přibyly řádky `SDT děj` (`SprayDroneSound.watch`, jen klient, stejný přepínač `SprayDroneSound.LOG`): nastoupení a vystoupení, skládání vleku, stav a mise dronu,
míchání / plnění / výměna baterie, centrála, přečerpávání, bedna, vypouštění na zem, nalévání z kanystru, začátek a konec pohybu hladiny každé nádrže a tok vodní hadicí
(`tok začal` / `tok skončil` s litry). Akce hráče se zapisují ve vstupních bodech (klávesy Alt+1, 2, 5, 7, 8, 0, B, Ctrl+I, X, R, klik na bednu, příkaz vleku, příkaz bedny, relé tyč, displej).
Ladicí kroky: `mark:<kód>` (řádek `SDT KROK`), `attachMax`, `selectMax`, `enterMax`, `enterPickup`, `leaveSeat`, `ownField`, `selectField`, `fieldInfo`, `lookBox`.
Přehled „akce -> důsledky“ z logu skládá `tmp/prubeh.py` + `tmp/build_prubeh.py` (kroky a texty v `tmp/prubeh_kroky.py`, průchod v `tmp/prubeh_run.ps1`).

Opravy z průchodu:
- **Nafta a plán trasy:** po změně hladiny nafty o víc než `ROUTE_DIESEL_STEP` (2 l), nebo přes nulu, se plán trasy přepočítá (`onFillUnitFillLevelChanged`); dřív start dál hlásil „došla nafta“,
  dokud se znovu nevybralo pole.
- **Alt+1 bez hlášky:** když nejde vypustit žádný dron, ukáže se důvod (`SprayDroneStation.getDrainBlockReason`): dron nestojí rozložený na plošině nebo je v misi, je prázdný,
  nádrž vleku drží jiný přípravek, nádrž vleku je plná (`sdt_warning_drain*`).
- **Vápno na zem (Ctrl+I):** koncentrát `SDT_FINE_LIME` se vypouští do pytlů `objects/limeBag/limeBag50.xml` (50 l, rozestupy na zemi v `SprayDroneToolbox.LIME_BAGS`); pytle se do bedny nevsávají (jen povolené druhy) a nakloněný
  pytel nad hrdlem koncentrátové nádrže vápno do ní vrací (jako kanystr s hnojivem).
- **Klávesy v tahači:** Alt+1, 2, 5 (a 6, kterou mod už nepoužívá) má v `inputBinding.xml` i FS25_EnhancedVehicle (ovládání zadního a předního nářadí); v tahači s vlekem mod tyto klávesy nedostane (Alt+5 tam rozloží vlek).
  Je to konflikt dvou módů, řeší se přemapováním v nastavení ovládání.

## Skenování pole (2026-10-22, krok 1: režim skenu a mapa pole; ve hře ověřeno na Maxu přes debug příkazy, multiplayer ne)

> **Od 2026-10-28 (etapa 0b, `docs/NAVRH-dron-predmet.md` kap. 10) sken dělá jen skenovací dron (varianta `K`)**, postřikový dron skenovat neumí: `missionMode` se odvozuje z typu dronu na plošině,
> nastavení „Mise“ v plánovači je šedé. Zbytek kapitoly (mapa, podmínky, vzorkování) platí beze změny; text níž, který mluví o přepnutí režimu dronu, je historický. Ve hře neověřeno.

Krok 1 ze tří (Pavlem schválený návrh): dron pole přeletí a z toho vznikne mapa pole na farmu. Krok 2 (postřik, vápno a hnojivo jen podle mapy, rezerva
podle RTK) a krok 3 (překryv mapy v plánovači, přehled polí, stáří dat) na mapu navazují přes API níže.

**Mise v plánovači:** nastavení `missionMode` (`Mise: postřik / sken pole`) a `scanCell` (`Sken: nízko 5 m / středně 10 m / vysoko 20 m`, výchozí 10 m), obě v `SprayDroneStation.SETTINGS`
s `idleOnly` (za mise se nemění; `isSettingEnabled` je šedí, `setSprayDroneSettings` jejich změnu za mise ignoruje). Ukládají se s ostatním nastavením (`flightSettings#missionMode`, `#scanCell`).
`SprayDroneStation.applyMissionMode` při skenu přepíše `workWidth`, `sprayHeight`, `sprayingSpeed` podle úrovně (`SprayDroneScanMap.LEVELS`: buňka 5 / 10 / 20 m, výška 8 / 15 / 30 m,
záběr = dvě buňky 10 / 20 / 40 m, rychlost `sprayDrone#scanSpeed` (výchozí 10 m/s) × 0,6 / 1 / 1,5); postřikové hodnoty dronu drží `sprayWorkWidth`, `sprayFlightHeight`, `sprayFlightSpeed`.
Trasu staví týž plánovač pruhů (`SprayDroneRoute.buildLegs`) s pseudo druhem postřiku `SprayDroneStation.SCAN_TYPE` (index 0; `getSprayType` ho v režimu skenu vrací, `getIsWorkable`
bere celé pole včetně zralého porostu). Paměť pokrytí má pro pole jeden záznam, takže přepnutí postřik / sken smaže rozpracovanou paměť toho druhého (stejně jako změna přípravku).

**Let:** dron letí s tím, co má v nádrži, nedoplňuje se (`pumpDrone` v režimu skenu nečerpá), nestříká (bez mlhy a zvuku postřiku) a nevrací se kvůli prázdné nádrži. Plán počítá s „plnou
nádrží“ a spotřebou 0,0001 l/m, ale hmotnost náplně je skutečná (`getFlightParams`: `massPerLiter` = náplň dronu / kapacita), takže prázdný dron letí na baterii zhruba třikrát déle
(odběr roste s kvadrátem hmotnosti) a dosah (`updateRange`) je větší. Stav dronu v HUD: „skenuje pole“. Pole: jen vlastní (`sdt_warning_scanOwnOnly`), zakázky ne.

**Podmínky** (`SprayDroneScanMap.getBlocker`): `environment.isSunOn == false` → tma, `weather:getIsRaining()` nebo `getRainFallScale() > 0,05` → déšť, vítr nad `sprayDrone#scanMaxWind`
(výchozí 12 m/s) → vítr. Vítr se čte z `weather.windUpdater.currentVelocity` (ve hře ověřeno: pole existuje, 2,78 při mírném větru; posluchač `addWindChangedListener` se ozve až
při změně větru). Start (Alt+8 i tlačítko plánovače, `startFlight`) se odmítne blikající hláškou `sdt_warning_scan{Dark,Rain,Wind}`, server to kontroluje znovu v `startNextBatch`;
za letu `checkScanConditions` jednou za 2 s, při překážce mise končí návratem domů se statusem `STATUS_SCAN_{DARK,RAIN,WIND}` (16–18; `STATUS_SCAN_DONE` 15, `STATUS_NUM_BITS` je 5).

**Vzorkování** (server, `SprayDroneStation.flushScan` místo postřiku pruhu): `SprayDroneScanMap.scanStrip` projde buňky, jejichž střed leží v pruhu (podél [0, délka), napříč do půl záběru),
a každou navzorkuje (`sampleCell`): vanilla `FieldState.new()` + `update(střed buňky)` (plodina, růst, plevel, hnojení, vápno, kameny; s Precision Farming jde přes jeho přepis
`FieldState.update`) a podíl pixelů plevele v celém čtverci buňky (`SprayDroneStation.getWeedPixels`, i neviditelné stavy 1–2). Mapy PF (dusík, pH) se nečtou.

**Mapa** (`scripts/SprayDroneScanMap.lua`, `SprayDroneScanMap.maps[farmId][fieldId]`): mřížka zarovnaná na násobky buňky (`originX/Z` = obdélník pole dolů na násobek, `nx`, `nz`),
`inside[index]` = střed buňky v polygonu pole (dopočítá se z pole, i u klienta), `values[index]` = zabalená hodnota, `times[index]` = čas skenu buňky, `updated` = poslední zápis.
Index buňky = `iz * nx + ix + 1`. Čas v herních minutách: `currentMonotonicDay * 1440 + dayTime / 60000`. Nový sken se stejnou buňkou buňky přepisuje, s jinou buňkou vznikne nová mapa.
Zabalená hodnota (pod 2^28, poziční zápis, `SprayDroneScanMap.FIELDS`): `weedShare` 0..15 (podíl plevele × 15, nenulový plevel nejméně 1), `weedState` 0..15, `sprayLevel` 0..3, `limeLevel` 0..3,
`growthState` 0..31, `fruitTypeIndex` 0..255, `stoneLevel` 0..7.

**API pro kroky 2 a 3:**
- `getMap(farmId, fieldId)`, `getCellIndex(map, x, z)`, `getCellCenter(map, index)`, `getCell(map, x, z)` → `{ weedShare 0..1, weedState, sprayLevel, limeLevel, growthState, fruitTypeIndex,
  stoneLevel, time }` nebo nil (nenaskenováno), `forEachCell(map, fn(index, x, z, buňka))`.
- `getAgeHours(map[, now])`, `getNow()`, `getSummary(map)` → `cells, scanned, coverage, weedCells, invisibleWeedCells, weedShare, noLimeCells, unfertilizedCells, ripeCells, stoneCells`
  (`getIsRipe(buňka)` podle `min/maxHarvestingGrowthState` plodiny), `formatSummary(map)` (text do logu).
- Server: `ensureMap(farmId, field, cellSize)`, `scanStrip(...)`, `getBlocker(maxWind)`.

**Síť a uložení:** server posílá změněné buňky nejvýš jednou za 2 s (`SprayDroneScanEvent`: hlavička mřížky + až 400 buněk `{index, hodnota, čas}`, `reset` u nové mapy), nově připojeným
klientům všechny mapy (`FSBaseMission.sendInitialClientState`, připojeno jen když funkce existuje; **neověřeno**). Ukládá se do `sdtScanMaps.xml` ve složce savegame (připojeno
k `FieldManager:saveToXMLFile` / `loadFromXMLFile`): `<map farmId fieldId cellSize originX originZ nx nz updated>` a skupiny `<cells time="…">index:hodnota …</cells>` (šestnáctkově).

**Plánovač:** u skenu místo litrů a přípravku řádek „Sken: buňka, výška, záběr“; u pole s mapou „Mapa pole: naskenováno %, buňka, stáří“ a „Plevel % buněk (neviditelný v N), bez vápna %,
nehnojeno %“ (`getRouteSummary`: `isScan`, `scanLevel`, `scanSummary`, `scanAge`, `scanMapCell`). Překryv mapy na mapě plánovače je krok 3.

**Ladění** (`SprayDroneDebug.PLAY`): `scanMode`, `sprayMode`, `scanCell0..2`, `scanSetWeeds` (plevel stav 2 v západních 40 % obdélníku vybraného pole, jinde žádný), `scanInfo` (souhrn
a mapa plevele po buňkách do logu jako řádky `SDT MAPA`), `scanBlockDark/Rain/Wind/None` (vynucená překážka), `scanConditions` (naměřené podmínky a číselná pole `windUpdater`),
`droneCam` (hráč 25 m od dronu 1), `scanPlanner` / `scanPlannerClose` (plánovač jako z tabletu).

**Ověřeno ve hře** (slot 10, Max se dvěma drony, pole 13, buňka 10 m, 799 buněk v poli):
- Odmítnutí startu s vynucenou tmou a deštěm (hláška + `SDT akce`), přerušení za letu vynuceným deštěm: oba drony se vrátily se statusem `SCAN_RAIN`. Skutečná noc a skutečný déšť nezkoušeny.
- Sken celého pole oběma drony (2 dávky na dron): 788 z 799 buněk (99 %; 11 nenaskenovaných buněk na šikmém západním okraji, kam plánovač pruhů nedosáhne), plevel přesně
  v nastavených západních sloupcích (196 buněk, všechny „neviditelný“), mapa v logu odpovídá tvaru pole. Status `SCAN_DONE` a souhrn v `SDT děj`.
- Uložení hry → `sdtScanMaps.xml`, restart → mapa načtená se stejným souhrnem; plánovač po restartu ukazuje režim skenu, plán (2 dávky, 5,6 min, baterie 19 % na dávku) a souhrn mapy.
- Přepínání úrovní a návrat na postřik obnoví záběr 11 m, výšku 3 m a rychlost 7 m/s.

**Neověřeno:** multiplayer (event, synchronizace při připojení), Middle a Mini, buňky 5 a 20 m v letu, skutečné počasí (práh větru 12 m/s je odhad, jednotka `currentVelocity` je
podle větrné elektrárny m/s), vliv Precision Farming na hodnoty `FieldState` (PF je ve hře zapnuté, plevel seděl).

Snímky: `out/mod_build/sken_dron_ve_vzduchu.png` (dron 1 při skenu nad polem, bez mlhy), `out/mod_build/sken_planovac.png` (plánovač v režimu skenu se souhrnem mapy).

### Aplikace podle skenu (2026-10-22, krok 2; ve hře ověřeno na Maxu herbicidem i vápnem přes debug příkazy a Alt+8, multiplayer ne)

**Nastavení:** `applyMode` v `SprayDroneStation.SETTINGS` („Aplikace: celé pole / podle skenu“, `idleOnly`, nové pole `blockedBy = "missionMode"` = jen u postřiku,
`isSettingEnabled` ho při skenu šedí), ukládá se jako `flightSettings#applyMode`, jde v `SprayDroneSettingsEvent` s ostatními. Bez mapy pole nebo u přípravku bez výběru se letí
celé pole a plánovač to řekne (`getSpotProblem`: `noMap` / `product`, texty `sdt_spot_noMap`, `sdt_spot_noProduct`).

**Výběr buněk** (`SprayDroneStation.getSpotSelector`, vanilla data z mapy skenu, mapy PF se nečtou): herbicid = `weedShare > 0` nebo `weedState > 0` (i neviditelný plevel),
vápno = `limeLevel == 0`, hnojivo = `sprayLevel < g_fieldManager.sprayLevelMaxValue`. Nenaskenované buňky v poli se ošetří (bezpečná volba, počet je v plánovači), buňky se středem
mimo pole převezmou výběr od sousedů v poli (okraj pole).

**Maska trasy** (`SprayDroneRoute.newMask`, `isInMask`, `isSwathInMask`, `bridgeMaskGaps`): `SprayDroneStation.buildAllLegs` ji nastaví do `SprayDroneRoute.mask` na dobu
`buildLegs` (jako `reserved` a `signalCircles`), takže platí pro řádky, úvratě i ostrovy (`appendParts`). Vzorek pruhu po 2 m se stříká, když je některé místo záběru napříč pruhem
(±půl záběru, po půl buňce) do rezervy od vybrané buňky. Mezery mezi úseky kratší než `sprayDrone#spotGap` (výchozí 12 m) se přeletí se stříkáním, ať dron necuká; delší se
přeletí bez postřiku. Rezerva: `sprayDrone#spotMargin` (výchozí 6 m), s RTK `sprayDroneGpsConfiguration#spotMargin="1.5"` (Max a Middle, i v šablonách `blender/templates`).
Maska se drží v `spotMaskCache`, dokud se nezmění mapa (počet a čas buněk), přípravek, rezerva nebo záběr. Spotřeba herbicidu v plánu (`getFieldWeedFactor(self, mask)`) se počítá jen
z plochy masky; za letu se dál odečítá podle plevele pod pruhem. Pole hotové = maska nemá co ošetřit (stejně jako dřív bez masky, paměť pokrytí se pak smaže); oba drony na Maxu
si dělí jen vybrané úseky.

**Srovnání v plánovači:** `updateRoutePreview` při aktivní masce spočítá i plán bez masky (`updateFullPlan`, `spotOff` na dobu výpočtu, výsledek `routeFull` po dronech, v
`getRouteSummaryAll` se litry sčítají a minuty berou nejdelší). Souhrn má `spot` (vybrané / všechny / nenaskenované buňky, rezerva, stáří mapy, `stale` nad `sprayDrone#spotMaxAge`
= 48 h, `fullLiters`, `fullMinutes`); řádky dává `SprayDroneStation.getSpotTexts` („Podle skenu: X z Y buněk…“, „Celé pole A l / B min · podle skenu C l / D min“, varování
o stáří). Stará mapa jen varuje, aplikaci nebrání. Od 2026-10-22 si mapa ošetřené buňky pamatuje (viz „Ošetřené buňky v mapě skenu“), takže další mise podle téže mapy
už nelétá nad vyřešenými buňkami.

**Záznam:** při startu `SDT děj: aplikace podle skenu, pole N: X z Y buněk (nenaskenováno Z), rezerva R m, stáří mapy H h` (nebo proč nejde), na konci
`SDT děj: aplikace podle skenu na poli N hotová`.

**Ladění** (`SprayDroneDebug.spotCommand`): `spotOn`, `spotOff`, `spotFillHerbicide`, `spotFillLime` (hlavní nádrž plná, drony prázdné), `spotLimeSet` (vápno 0 v západních
40 % obdélníku pole, jinde max), `spotLogStart` (od teď se zapisují postříkané pruhy z `flushSpray`), `spotInfo` (maska, plán a srovnání, řádky plánovače, postříkané metry a litry
západně / východně od řezu 40 %, plevel a průměr vápna v obou částech).

**Ověřeno ve hře** (slot 10, Max se dvěma drony, pole 13, mapa s buňkou 10 m, bez RTK = rezerva 6 m):
- Herbicid, plevel v západních 40 %: maska 207 z 799 buněk (196 s plevelem + 11 nenaskenovaných). Plánovač: 2 dávky, 2,64 ha, „Celé pole 183 l / 14 min · podle skenu 128 l / 6 min“.
  Postřik: západ 1 701 m pruhů / 86 l, východ 701 m / 9 l (pruhy přes řez kvůli rezervě, záběru a šikmým řádkům). Plevel na západě ze 100 % pixelů na 2,5 %, ve zbytku pole 0,2 → 0 %.
  Konec mise hlášením „pole hotové“ u obou dronů.
- Vápno (`spotLimeSet`, nový sken: 196 buněk bez vápna): plánovač „Celé pole 5 178 l / 67 min · podle skenu 1 712 l / 22 min“, postřik 1 708 l (západ 1 211 l, východ 497 l),
  vápno na západě z 0 na průměr 2,94 (max 3). Konec „pole hotové“.
- Krátká druhá mise herbicidu podle nového skenu: maska 33 buněk (zbytek plevele na okrajích).

**Neověřeno:** RTK (rezerva 1,5 m) ve hře (zkoušeno jen bez hry, `tmp/test_spot.py`), hnojivo podle skenu, multiplayer (maska se počítá na klientu z mapy skenu), Middle a Mini,
mapa s buňkou 5 a 20 m pro aplikaci.

Snímky: `out/mod_build/spot_planovac.png` (plánovač s herbicidem podle skenu, srovnání plánů a mapou plevele), `out/mod_build/spot_planovac_vapno.png` (totéž u vápna),
`out/mod_build/spot_dron_postrik.png` (dron stříká nad pásem pole, vlevo už vápněné pruhy, vpravo neošetřená půda), `out/mod_build/spot_dron_postrik2.png` (hranice vápněné
a nevápněné části pole, dron nad ní).

### Mapa skenu v plánovači (2026-10-22, krok 3; ve hře ověřeno na Maxu a Middle přes debug příkazy, multiplayer ne)

`scripts/gui/SprayDroneScanOverlay.lua` (metody `SprayDronePlannerScreen`, načítá se na konci souboru plánovače).

**Překryv:** na mapě plánovače se pod obrysy polí a trasou kreslí buňky všech map skenu farmy vleku, které jsou aspoň zčásti na obrazovce (`drawScanOverlay`), podle zvolené
vrstvy: plevel (bez plevele / do 25 % / nad 25 % / neviditelný ve fázi 1–2), vápno (potřebuje / vápněno), hnojení (`sprayLevel` 0 / 1 / 2+), zralost (bez plodiny / mladý porost
pod polovinou `minHarvestingGrowthState` / roste / zralé / po sklizni nebo uschlé nad `maxHarvestingGrowthState`), kameny, pokrytí; „Vypnuto“ překryv skryje. Nenaskenované buňky
v poli jsou světle šedé (u vrstvy pokrytí červené). Buňka starší než `STALE_HOURS` (48 herních hodin, podle času skenu buňky) je vybledlá (k šedé, krytí × 0,45) – při novém
skenu je vidět, kudy už dron prošel. Kreslení: `buildRects` slije souvislé úseky řádku se stejnou barvou a stejné úseky sousedních řádků do jednoho obdélníku, výsledek je
v cache podle mapy (přestaví se po změně `updated` / `numScanned` / vrstvy, kvůli stárnutí nejpozději po 5 s). Mapa plánovače je otočená severem nahoru, obdélníky se kreslí
přímo `drawFilledRect` mezi dvěma rohy přepočtenými `worldToScreen`.

**Volba vrstvy a přehled polí** (od 2026-10-23 v levém panelu plánovače, viz „Plánovač letu“ > Rozložení): vrstva se volí na stránce
Mapa skenu (seznam jako legenda herní mapy), přehled polí je stránka Pole (řádek = nejnaléhavější nález a stáří mapy, řazení podle
naléhavosti z `getShares`: plevel × 3 + zralé × 3 + bez vápna × 1,5 + nehnojeno). Dřívější lišta čipů vlevo nahoře (`drawScanUi`)
a tabulka přehledu (`drawScanOverview`) jsou pryč. Vrstva se pamatuje po dobu hry (instance plánovače), výchozí je plevel.

**Notifikace:** konec skenu (`STATUS_SCAN_DONE`) místo obecného „sken je hotový“ ohlásí souhrn pole (`sdt_scanui_notify`: „Pole 13 naskenováno: plevel 25 % (neviditelný 25 %),
bez vápna 100 %, nehnojeno 0 %, zralé 0 %“, podíly naskenovaných buněk; `SprayDroneScanOverlay.getFindingsText`). Server před koncem mise pošle klientům poslední buňky
(`SprayDroneScanMap.flushSync` v `startNextBatch`), aby souhrn u klienta počítal s celou mapou.

**Ladění:** `scanLayerOff/Weed/Lime/Fert/Ripe/Stone/Cover`, `scanOverview` (stránka Pole a výpis řádků do logu), `scanOverviewOff` (stránka Mapa), `scanOverviewPick` (klik na první řádek),
`scanAge` (mapa vybraného pole o 72 h starší), `scanPlannerMiddle` (plánovač Middle). Akce v `SDT akce`: přepnutí vrstvy, přehled, klik na pole, text notifikace.

**Ověřeno ve hře** (slot 10, Max, pole 13, mapa z kroku 1): všechny vrstvy (plevel na západní části fialově, vápno celé pole „potřebuje“, zralost „bez plodiny“, pokrytí),
přehled s řazením a klik na řádek (vybere pole, posune mapu), vybledlá data po `scanAge`, nový sken za otevřeného plánovače (čerstvé buňky syté vedle vybledlých),
notifikace se souhrnem po `SCAN_DONE`, plánovač Middle s přehledem (lišta a přehled se vejdou vedle panelu). Bez chyb Lua v logu.
**Neověřeno:** multiplayer (notifikace u klienta, pořadí eventu buněk a statusu), skutečné kliky myší (jen ladicí příkazy volající tytéž metody), více vlastních polí v přehledu
(slot 10 má jen pole 13), malé rozlišení (lišta se zalamuje, přehled může narazit na legendu mapy vlevo dole, když se do panelu nevejde), Precision Farming a vrstva vápna/hnojení
(s PF jde vápno a dusík přes jeho mapy, vanilla `limeLevel` / `sprayLevel` nemusí odpovídat).

Snímky (`out/mod_build/`): `sken_ui_plevel.png` (vrstva plevele), `sken_ui_vapno.png`, `sken_ui_hnojeni.png`, `sken_ui_zralost.png`, `sken_ui_pokryti.png`, `sken_ui_prehled.png`
(přehled polí), `sken_ui_stara_data.png` (vybledlá data, mapa posunutá na pole klikem v přehledu), `sken_ui_behem_skenu.png` a `sken_ui_behem_skenu_plevel.png` (nový sken:
čerstvé buňky vedle vybledlých), `sken_ui_middle.png` (plánovač Middle s přehledem).

### Počasí pro postřik (2026-10-22; ve hře ověřeno na Maxu přes debug příkazy a Alt+8, skutečné počasí a multiplayer ne)

Postřik a vápnění mají stejné podmínky jako sken, jen bez tmy (drony stříkají i v noci) a s nižším prahem větru kvůli úletu postřiku.
`SprayDroneStation.getWeatherBlocker(self, scanning)` (nahradila `getScanBlocker`) volá `SprayDroneScanMap.getBlocker(maxWind, allowDark)`: sken `scanMaxWind` (12 m/s) a tma
blokuje, postřik práh `sprayMaxWind` varianty dronu (`VARIANT_FLOATS`, atribut v `drone(?)` u Maxe, Middle i Mini a v šablonách `blender/templates`: S 5, M 6, L 7 m/s; společný
výchozí `sprayDrone#sprayMaxWind` 6). Start (`startFlight`) i server (`startNextBatch`) odmítnou se statusem / hláškou podle druhu mise (`getWeatherStatus`, `getWeatherWarning`:
postřik `STATUS_SPRAY_RAIN` 19 / `STATUS_SPRAY_WIND` 20, texty `sdt_warning_spray{Rain,Wind}`, `sdt_status_spray{Rain,Wind}`). Za letu `checkWeather` (dřív `checkScanConditions`)
každé 2 s (`WEATHER_CHECK_TIME`, pole `weatherCheckTime`) pro postřik i sken: překážka = konec mise a návrat domů.
**Jednotka větru:** mapy mají `<wind speed>` v km/h (mapUS jaro: slunečno 4–13, zataženo 17–28, déšť 38–68, tornádo 120) a `windUpdater.currentVelocity` je m/s (speed 10 → 2,78).
Prahy postřiku proto padají do zatažených dnů (4,7–7,8 m/s: malý dron nestříká už od CLOUDY, velký až při CLOUDY_DENSE), sken 12 m/s zastaví prakticky jen déšť, který ho zastaví i tak.
**Plánovač:** řádek „Počasí: vítr X m/s (limit Y m/s) – lze letět / příliš fouká / prší / tma (sken potřebuje světlo)“ (`getWeatherText`, `sdt_planner_weather`, `sdt_weather_*`), při překážce červeně.
**Ladění:** `weatherInfo` (podmínky, prahy skenu a postřiku, řádek plánovače), `wind3/6/8/10/15` a `windOff` (vynucený vítr, `SprayDroneScanMap.debugWind`), `scanBlockDark/Rain/None`
platí i pro postřik (vynucená tma postřiku nevadí).
**Ověřeno:** Max s dronem L (práh 7): vynucený vítr 10 m/s → Alt+8 odmítnut „Na postřik fouká příliš silný vítr“, plánovač červeně „vítr 10.0 m/s (limit 7 m/s) – příliš fouká“; vynucený déšť →
odmítnut „V dešti dron nestříká“; vynucená tma → postřik startuje; vítr 10 m/s za letu → oba drony přerušily postřik a vrátily se se statusem `SPRAY_WIND` (notifikace „postřik přerušen,
fouká příliš silný vítr“). Middle (dron M) ukazuje limit 6 m/s. **Neověřeno:** skutečný vítr a déšť z počasí hry, Mini, multiplayer.

### Ošetřené buňky v mapě skenu (2026-10-22; ve hře ověřeno na Maxu a Middle s RTK, multiplayer ne)

Postřik pruhu (`flushSpray`, spot i celé pole) na poli s mapou skenu zavolá `SprayDroneScanMap.treatStrip`: buňky se středem pod záběrem se znovu přečtou ze skutečného stavu pole
(`readCell` = totéž co sken: `FieldState` + pixely plevele; nic se nedopočítává, vanilla třeba nedovolí druhé hnojení před dalším růstem) a dostanou záznam ošetření `treated[index]`
(herní minuta) a `treatedKinds[index]` (bity `TREAT_HERBICIDE` 1, `TREAT_LIME` 2, `TREAT_FERTILIZER` 4, `getTreatKind(sprayType)`). Čas skenu buňky zůstává; nový sken buňky ošetření smaže.
**Výběr:** `getSpotSelector` buňku ošetřenou týmž přípravkem do dalšího skenu nevybere (i nenaskenovanou), takže druhá mise podle stejné mapy už nelétá nad vyřešenými buňkami.
Na konci aplikace („pole hotové“) `treatRemaining` označí buňky, které přípravek pořád vybírá, ale trasa je pokrýt nedokázala (okraj pole, kam pruhy nedosáhnou; na poli 13 šest buněk)
– jinak by nad nimi každá další mise marně létala. Za mise je maska zmrazená (`spotMaskCache.frozen`), aby ošetřením zmenšená maska nevyhodila sousední pruh, který dostříká zbytek buňky.
Mimo misi `refreshDroneRoutePreview` přepočítá plán, když se změní `revision` mapy (ošetření jiným vlekem, data ze serveru); `revision` zvedá sken, ošetření i data ze serveru a podle ní
se přestaví maska i překryv.
**Síť a uložení:** buňka v `SprayDroneScanEvent` je `{index, hodnota (nil = nenaskenováno), čas skenu, čas ošetření (nil), druhy}`, savegame `<treated>index:čas:druhy …</treated>` (šestnáctkově) v `<map>`.
**Plánovač:** vrstvy plevel / vápno / hnojení kreslí buňky ošetřené jejich přípravkem modře („ošetřeno po skenu“, `sdt_scanui_c_treated`); souhrn a přehled polí počítají ze skutečných
přečtených hodnot, takže ošetřené buňky jsou „vyřešené“ a zbytky na okraji jsou vidět. `formatSummary` má „ošetřeno po skenu N“. Ladění: `scanTreatedInfo` (počty podle druhů, maska),
`scanInfoFert` (hnojení po buňkách: mapa | skutečnost), `spotFillFertilizer`, `spotFertSet` (hnojení 0 v západních 40 %, jinde max), `spawnMiddleRtk`, `targetMax` / `targetMiddle`
(komu patří příkazy průchodu hrou, když je víc vleků).
**Ověřeno ve hře** (slot 10, pole 13, buňka 10 m):
- Max, herbicid podle skenu (207 buněk): po misi 280 buněk ošetřeno (včetně 11 nenaskenovaných), maska 0, plán 0 dávek, Alt+8 → „pole hotové“, plánovač ukazuje modrou plochu.
  (Mezistupeň kódu: okrajové buňky řešilo rozšíření pruhu o třetinu buňky, ve finální verzi je místo něj `treatRemaining`, ověřené u hnojiva níž.) Úplně první verze
  nechala 3 okrajové buňky s plevelem vybrané a každá další mise je marně přelétala (plán 4 l).
- Max, hnojivo podle skenu (196 buněk na úrovni 0): jedna mise, mapa po buňkách přesně odpovídá poli (`scanInfoFert`: všude kromě nenaskenovaných buněk shodné), maska 0,
  druhý start → „pole hotové“ (vanilla druhé hnojení hned po prvním nepřičte, úroveň 1 zůstane do dalšího růstu a nového skenu). Hnojivo podle skenu tím ověřené.
- Uložení hry → `<treated>` v `sdtScanMaps.xml`, restart → „ošetřeno po skenu 247“ načteno a plán herbicidu podle skenu 0 dávek.
- **Middle s RTK** (`spawnMiddleRtk`: rezerva 1,5 m, jeden dron M, záběr 9 m; mezistupeň kódu jako výš): sken 788/799 buněk, herbicid podle skenu 207 buněk, plánovač „Celé pole 155 l / 30 min · podle skenu 110 l / 14 min“,
  postřik západ 2 228 m / 73,8 l, východ jen 371 m / 3,3 l (Max bez RTK: 701 m / 9 l), plevel na západě ze 100 % na 2,6 %, pak maska 0 a „pole hotové“. RTK a Middle s jedním dronem ověřeny.
- **Buňky 20 a 5 m za letu** (Max): 20 m → 200 z 209 buněk za 35 s skutečného času (rychlost hry 6), 5 m → 3 161 z 3 178 buněk (99 %) za 7,5 min; mapa a překryv v plánovači v pořádku.
**Neověřeno:** multiplayer (nový formát eventu), vápno po ošetření (kód stejný jako u hnojiva, vápno bylo ověřeno v kroku 2), Mini.
**Snímky** (`out/mod_build/`): `pocasi_odmitnuti_vitr.png` a `pocasi_odmitnuti_dest.png` (blikající hláška při Alt+8), `pocasi_planovac_vitr.png` (řádek počasí červeně),
`pocasi_navrat_vitr.png` (notifikace obou dronů „postřik přerušen, fouká příliš silný vítr“), `mapa_osetreno_plevel.png` (vrstva plevele po herbicidu: modrá ošetřená část, „0 z 799 buněk“,
„pole je hotové“), `mapa_osetreno_hnojeni_1.png` (totéž u hnojení), `overeni_hnojivo_planovac.png` (hnojivo podle skenu před misí, 207 buněk), `overeni_middle_rtk_planovac.png`
a `overeni_middle_rtk_po.png` (Middle s RTK před a po herbicidu, rezerva 1,5 m), `overeni_bunka20.png` a `overeni_bunka5.png` (mapa plevele s buňkou 20 a 5 m).

## Dron na plošině za hry (2026-10-22, etapa 0 návrhu `docs/NAVRH-dron-predmet.md`; ve hře ověřeno na Maxu a Middle přes debug příkazy, multiplayer jen zkouškou proudu)

- **Stav plošin** `spec.pads` (sdílené pole): varianta dronu na plošině 1 / 2 (`"S"`, `"M"`, `"L"`, `""` = prázdná). Plošina 1 = dron 1, plošina 2 = dron 2
  (jen vlek s bloky `drone(?)#slot="2"`, tedy Max). Při koupi ji naplní konfigurace `sprayDrone`, v uložené hře je `.pad(?)#drone` (`none` = prázdná) a má
  přednost; `#configDrone` je dron z konfigurace při uložení – když se v dílně změní, uložené plošiny neplatí. `#batteryVariant` drží typ baterií
  (u prázdné plošiny 1 zůstává z posledního dronu).
- **Výměna** `SprayDroneStation.setPadDrone(self, padIndex, name)` (server, `scripts/SprayDronePadDrone.lua`): kontrola `getPadsProblem` (známá varianta,
  na Maxu obě plošiny stejná velikost – parametry letu jsou sdílené –, plošina 2 jen s dronem na 1) a `getPadBlocker` (nic v misi, nic mimo plošinu,
  žádné přečerpávání ani přenos baterie, dron na té plošině složený = složený vlek). Pak `applyPads`: dron 2 pryč / znovu (`loadSecondDrone`), dron 1
  znovu (`selectPadVariants`, `loadVariantParameters`, `loadChargeParameters`, uzly, vrtule, zvuky a mlha, hadice, úchyty, kamera, `initDroneFold`),
  baterie si nechají nabití v podílu a dostanou model nové velikosti. Náplň vyměněného dronu se zahodí. Hlášky `sdt_pad_*`.
- **Prázdná plošina**: `hasDrone = false`, Alt+8 je teď registrované i bez dronu a hlásí `sdt_pad_noDrone`, plánovač místo řádku dronu napíše „Na plošině
  není dron“.
- **Síť**: `writeState` začíná plošinami a typem baterií (2 bity na plošinu + 2 bity), `readPads` při rozdílu volá `applyPads` dřív, než se čte zbytek
  proudu (počet dronů). Změnu zatím spouští jen server (ladicí příkaz); event od klienta přijde s etapou 1.
- **Ladění**: `pad1None/S/M/L`, `pad2None/S/M/L`, `padInfo` (plošiny, parametry, drony, baterie do logu), `padCam`, `padStream` (stream* funkce se
  nahradí frontou: zápis stavu pro připojení, rozhození plošin na L/L, čtení zpět; sedí, když se přečte stejně hodnot stejného druhu).
- **Ověřeno ve hře** (slot 10): Max L/L → odmítnutí na rozloženém vleku, složení, L/- → S/-, smíšené S/L odmítnuto, S/- rozložení, baterie se nabije do dronu,
  sken jen dronem S (plánovač: nádrž 20 l, dosah 300 m, část pole mimo dosah), S/- → L/L (odmítnutí „-/L“), sken oběma drony L a postřik herbicidem podle
  skenu oběma drony (pole hotové), M/- uloženo a po restartu načteno přes konfiguraci L (i s `#configDrone`), Middle M → S → žádný (Alt+8 odmítnut,
  plánovač „Na plošině není dron“) → M a rozložení. `padStream` na Maxu (S/-, M/-) i Middle (prázdná): 150 / 151 / 145 hodnot, 0 chyb, plošiny zpět.
- **Neověřeno**: skutečný multiplayer, Mini, kamera C na skrytém dronu, změna dronu v dílně po uložení (jen kód), let s dronem M po výměně.
- **Snímky** (`out/mod_build/`): `plosina_max_LL_rozlozeny.png`, `plosina_max_S_prazdna_slozeny.png`, `plosina_max_S_prazdna_rozlozeny.png`,
  `plosina_max_S_planovac.png`, `plosina_max_LL_po_vymene.png`, `plosina_max_LL_planovac_sken.png`, `plosina_max_LL_planovac_postrik.png`,
  `plosina_max_M_prazdna_pred_ulozenim.png`, `plosina_max_M_po_nacteni.png`, `plosina_max_M_planovac_po_nacteni.png`, `plosina_middle_zadny_alt8.png`,
  `plosina_middle_zadny_planovac.png`, `plosina_middle_M_rozlozeny.png`.

## Stavba vleků z knihovny dílů a cache pečení (2026-10-23)

Příkazy se nemění: `blender.exe -b --python blender\headless_middle.py` (`headless_max.py`, `headless_mini.py`; `-- build`,
`-- export`, `--no-bake`). Novinky (podrobně `docs/NAVRH-dily.md`, kap. 6):
- Centrála, indukční nádrž, čerpadlo, hlavní nádrže Middle, vápenná nádobka a věšák Maxu, mixér Mini, pneu a disky se staví
  přes `blender/parts_lib.py` (`PL.call(funkce, …)`): každý díl ve vlastním procesu Blenderu do cache `blender/parts/`
  (v gitu není), znovu jen když se změní zdroj dílu nebo modulu, který importuje, parametry nebo konstanty, které vlek přepsal.
  Výsledek je ověřeně stejný jako stavba bez knihovny (`SDT_PARTS=0` ji vypne).
- Druhá etapa (kap. 7 v `docs/NAVRH-dily.md`): díl je jeden model v lokálním počátku a vlek ho jen umístí (`at=PL.Place.at(x, y, z)`, otočení,
  zrcadlení, `rename`); centrála je jedna (Max ji staví dvakrát, druhou zrcadlově), mlýnek, pumpa, násypka, dron a baterie jsou rozseknuté
  na díly (39 karet v katalogu). Rovnocennost ověřená po vrcholech scény a exportem do `tmp` (XML vleků Mini, Middle, Max shodné s módem).
- vmask se peče jen při změně geometrie, DirtUV nebo materiálů (`blender/parts/bake/`); `SDT_FORCE_BAKE=1` / `--force-bake`
  vynutí pečení. Opakovaný export beze změny: Middle ~1 min, Max ~1,5 min, Mini ~20 s (dřív 3,5–5 min s pečením).
- Náhled jednoho dílu: `blender.exe -b --factory-startup --python blender\parts_lib.py -- preview <díl>.blend <png>`.
- Pozor: vmask vleku v módu u Middle a Maxe je starší než geometrie (export s `--no-bake`); příští plný export ho opraví.

## Obrazový katalog modelů (2026-10-23, přepracováno na snímky z GIANTS Editoru)

Katalog (`out/katalog/index.html`, nasazený na `https://fs25-relay.tail372622.ts.net/static/sdt-katalog/`) ukazuje **snímky z GIANTS Editoru
(GE)**, tedy z enginu hry: modely se načtou z i3d (vozidla a objekty z módu, díly z knihovny vyexportované do `tmp/ge/parts`) a nafotí se
16 pohledů (zepředu, zezadu, zleva, zprava, shora, zespodu, dvě izometrie, čtyři pohledy pod 45° shora a čtyři zespodu). Blender se
použije jen pro rozložený stav vleků a dronů (vzniká animací ve hře, v GE nejde) a karta to u něj píše. Celý postup (příkazy, Lua
funkce pro GE, plán záběrů, co v GE nejde) je v `docs/NAVRH-dily.md`, sekce 8.

- `python tools/katalog.py` postaví každý model ve skrytém Blenderu (priorita BELOW_NORMAL; stejné build skripty a knihovna dílů jako
  export), uloží data o modelech a dílech (`out/katalog/data`) a vyrenderuje rozložené stavy; `mod/` ani `.blend` se nemění. Jen vybrané
  úlohy: `python tools/katalog.py middle pump`, jen stránka: `--page` (PNG z `out/ge` převede na JPG 1 280 px a náhledy 400 px).
- Karty: Vleky (3), Drony (3), Díly vleků (39, jedna karta na díl, varianty jsou záložky, u každého dílu „kde a jak je použit“,
  rozdělené do skupin: elektrocentrála a rozvody, nádrže a čerpadla, kola, mlýnek, pumpa a násypka, dron, baterie) a Vybavení a objekty
  (13: mlýnek, pumpa, násypka, foukací roura, pytel, relé tyč, tablet, tři kanystry, tři baterie). Údaje: trojúhelníky a objekty,
  materiály a obrázky z Blenderu, soubory z i3d, uzly z `i3dMappings` XML, jména uzlů hledaná v Lua.
- Díly dronu v knihovně (`build_drone.part_fuselage`, `part_tank`, `part_arm`, `part_rotor`, `part_gear`, velikosti S, M, L) vznikají z
  `build_drone` (rozložený letový stav, jedna souřadná soustava) a slouží katalogu a exportu dílů; vlek dál staví dron přímo
  a export dronů se nezměnil.

## Vylepšení modelu dronu a úchyty lyžin na plošině (2026-10-23; jen model, XML a Lua, ve hře neověřeno)

Pavlovo zadání po prohlídce snímků z GE (`out/katalog/img/drone_L_*`). Stavba: `blender/build_drone.py` (S, M, L), úchyty
`build_pad_clamps` v `build_trailer_middle.py` (Max je volá pro obě plošiny).

- **Poziční světla**: kvádry 5 × 3 × 2 cm na koncích lyžin (`NavLight_L/R`, dekorace) zrušeny. U každého motoru je na straně ramene
  pouzdro s kulatou čočkou zapuštěnou do předního okraje (`<prefix>Led_i` je dnes tato čočka, `LedLight_i` bodové světlo před ní).
  Pouzdro je v meshi ramene, čočka samostatný mesh s materiálem `SDT_NavLed` (z `vmask` vyloučený, barva v barvě vrcholů `Col`).
  Barvy podle DJI Agras: rameno 1 (vpředu vlevo) červená, 2 (vpředu vpravo) zelená, 3 a 4 (vzadu) bílé; blikají dál zadní (`navLight#blink`).
  Názvy uzlů a XML (`navLight node/lightNode`) se nezměnily, Lua se nemění. Pouzdro stojí vedle ramene, ne přímo pod motorem, protože
  pod motorem visí náboj spodní vrtule nebo tryska (M má trysku pod všemi čtyřmi motory).
- **Úchyty lyžin**: `padClampL/R` a `padClampHingeL/R` (u druhé plošiny Maxu s příponou `2`), viz „Zajištění dronu na plošině“.
  Mini je nemá: dron tam leží ve skládací bedně, kterou zajišťuje sama (`mount_drone_on_tray`), takže příčka by byla navíc.
  Lua: `getPadClamps` v `SprayDroneService.lua` (konstanta `SprayDroneStation.CLAMP_NODES`); XML bez `objectChange` pro úchyty,
  animace `foldLadder` má pro úchyty dvě `<part>` (u Maxu čtyři).
- **Trup**: zaoblené rohy (poloměr 36 % menšího rozměru) a hrany (svislý profil po čtvrtkruhu), hladké stínování, plochý hřbet pro baterii zůstal.
- **Nádrž**: oblá bílá skořepina (zaoblený obdélník se zaoblenými rameny nahoře a dole, stěna mezi 30 a 80 % výšky zůstala rovinná kvůli
  polepům značky), hladké stínování, okénko stavoznaku zůstalo. Průsvitný proužek s hladinou se nedělal (potřeboval by průhledný materiál
  a vlastní UV).
- **Ramena** (S a L): hranatý regulátor se žebry nahradil plynulý kryt kolem ramene s drážkami (tmavé pásy); M regulátor nemá.
- **Listy vrtulí**: v GE přesvěcovaly (bílé pruhy) kvůli materiálu `calibratedGlossPaint` (clearCoat 0,5, smoothness 0,85) pod čtyřmi silnými světly
  editoru. Materiál `Prop_Blade` je dnes `plasticPainted` se `smoothnessScale` 0,55 (barvu a karbon dál přepíná `applyPropellerLook`).
- Polygony dronu (stavba vleku, bez zbytku vleku): S 9 000 → 10 400 (+15,6 %), M 11 600 → 12 776 (+10,1 %), L 12 024 → 13 424 (+11,6 %); úchyty
  504 → 280 trojúhelníků na plošinu.
- Změna rozložení ramen: `unfoldedRot` ramen se o 0,0–0,25° změnil (počítá se ze středu trupu, který je dnes přesně symetrický).

Katalog (2026-10-23): karty mají sekci „Co zlepšit“ z `tools/katalog_analyza.json` (štítek priority 1–3, filtr „Ke zlepšení“ řazený podle priority,
rozbalovací blok „Společné nedostatky“ nahoře); soubor se jen čte (`katalog.load_analysis`). Snímky před/po úpravě dronu a úchytů: `out/dron_v2/`.

## Přestavba pumpy, mlýnku a koncovky hadice podle katalogu, priorita 1 (2026-10-23; jen model, XML a Lua beze změny, ve hře neověřeno)

Podle `tools/katalog_analyza.json` (body `_spolecne`, `pump`, `part_pump_head`, `mill`, `part_mill_mill`, `part_mill_bin`, `part_hose_end`). Položky mají v analýze
`stav: opraveno` (oranžová fajfka „opraveno, čeká na schválení“ na kartě i v detailu; `schvaleno` = zelená; filtr „Ke zlepšení“ ukazuje stav a u priority počet hotových).
Snímky před/po: `out/modely_p1/srovnani_<model>.jpg` (před = `out/modely_p1/pred/*.png`), spirála na článcích hadice v GE: `out/modely_p1/hadice_spirala_clanky*.png`.

**Společné**
- „Vějíř“ na čelech válců **nebyl UV**. Čela jsou rovinně mapovaná (`_box_uv`), ale menší válec ležel čelem v téže rovině jako větší (těsnění na čele spojky Storz,
  čelo mlýna v přírubě) a v enginu se obě čela prolínala (z-fighting, černobílé či žlutočerné paprsky podle trojúhelníků vějíře). Oprava je na jednom místě,
  `Mesh._separate_caps` v `sdt_tanks.py` (`lathe` si pamatuje plochá čela, při `finish` se menší čelo o `Z_FIGHT_STEP` = 0,7 mm vysune před větší, vrcholy ve rovině čela
  včetně okraje pláště, takže bez mezery); platí pro všechny modely stavěné přes `Mesh` (vleky při dalším exportu).
- Materiály (`sdt_parts.MATERIALS`, `export_middle_mod.MATERIAL_MAP`): `SDT_AluCast` (litý hliník: `calibratedMatPaint`, matný, zrnitá detailní textura; nahradil `SDT_Alu` na tělese pumpy a
  spojkách), `SDT_PaintGrey` (nátěr násypky, cyklonu a šneku), `SDT_DeckPlate` (`steelTreadPlate`, tmavá protiskluzová paluba), `SDT_HoseSpiral` (hadice, viz níž). Nižší jas a lesk
  `SDT_PaintWhite`, `SDT_TankWhite`, `SDT_TankPE` (u vleků a dronů se projeví až po jejich exportu, teď se nic jiného než pumpa, násypka a mlýnek neexportovalo). Pozor: světla editoru jsou ~8×
  silnější než ve hře, takže `colorScale` v GE vyjde světlejší než ve hře (0,24 už je v GE bílá); hodnoty jsou laděné na vzhled v katalogu.
- Cedulky VSTUP / VÝSTUP / VÁPNO už nevisí na drátech: štítek je přišroubovaný na sloupku přímo na trubce u spojky (`build_pump.label_on_pipe`), VÁPNO na šikmé stěně lievku.
- Nová spojka `Mesh.storz(p, d, collar, scale)` (zmizelá `sdt_mlyn._storz` už neexistovala a pumpa ani násypka se z HEAD nedaly postavit): prstenec s drážkou, gumové těsnění
  3 mm před čelem, tři ploché packy, barevná objímka (modrá VSTUP, červená VÝSTUP, žlutá násypka), tmavý průvrt.
- GE drží i3d podle cesty: změněný soubor načtený podruhé ze stejné cesty se ve stejné relaci znovu nenačte (fotit z nové kopie, `tmp/p1/mk_ge_copy.py`).

**Pumpa** (`build_pump.py`, `waterPump.i3d`): rám z ohýbaných trubek (smyčky se zaoblenými rohy), gumová madla, čtyři patky; motor s vodorovným hřídelem (skříň, válec skloněný o 25° se žebry,
hlava a kryt ventilů, karburátor), skříňový vzduchový filtr vlevo, tlumič s krytem vpravo, červený kryt chlazení a startér s lankem a držadlem; zaoblená žlutá nádrž nad motorem s velkým
žebrovaným víčkem a stavoznakem; vpředu spirální skříň (`Mesh.scroll` s maticí osy Y) s výtlačným hrdlem, plnicí zátkou, vypouštěcím šroubem a tlakoměrem, sací krček s odbočkou na bok.
Porty: výtlak (−0,48; −0,12; 0,40), sání vstup (0,48; −0,34; 0,28); od 2026-10-23 bez rybníkové spojky (přední krček končí odbočkou na bok, uzel `pumpPondPort`, štítek a zelená objímka jsou pryč,
`pondHose*` nahradila koncovka `inStrainerEnd` na vstupní hadici, `i3dMappings` v XML jsou nová čísla),
rozměry 0,97 × 1,22 × 0,74 m (dřív 1,0 × 1,265 × 0,74). Trojúhelníky 16 808 → 17 368 (před zrušením rybníkové spojky). Hadicové články mají materiál `SDT_HoseSpiral`.

**Hadice a koncovka** (`sdt_mlyn._hose_end`, `part_hose_end`): spirálová výztuha je **normálová textura** `mod/…/textures/sdt_hose_normal.dds` (`tools/make_hose_normal.py`, jedna šroubovice na
dlaždici, alfa = x pro případ DXT5nm), takže počet trojúhelníků článků (40) se nemění; válcové UV (U po obvodu, V po délce, 5,5 závitu na 1 m článku, na koncovce 32 závitů/m)
nastavuje `Mesh.spiral`. Materiál: `rubberBlackHoses` s `clearCoat` 0,45 / 0,6 (lesk gumy). Koncovka: zmenšená Storz (měřítko 0,62) s těsněním a packami, kuželový přechod,
lisovaná objímka se dvěma šroubovými sponami a gumová ochrana ohybu. 1 900 → 2 140 trojúhelníků, 0,119 × 0,252 × 0,123 m. Odkaz na normálovou mapu je v i3d relativní (`../../textures/…`),
`export_middle_mod.NORMAL_MAPS` + `normal_map_ref`. Ve vlecích se nová koncovka objeví při jejich dalším exportu.

**Mlýnek** (`sdt_mlyn.py`, vozidlo `sdtLimeMill`): mlýn je kratší (`MILL_HL` 0,25, `MILL_X` −0,08; pravý konec u motoru se nehýbe) a má víko na dvou pantech vzadu, tři upínky vpředu, vyklenuté čelo
s výstupním hrdlem a přírubou (`MILL_OUT_X`), revizní dvířka dole; cyklon: kužel s obručemi, přírubové víko s vyústěním (koleno, filtrační rukáv), stoupačka od příruby mlýna s koleny a přírubami do boku válce,
klapka s protizávažím pod kuželem, spojka Storz, stavoznak (mosazné odbočky, skleněná trubice s plovákem, klec); násypka: kosé stěny (nálevka od výsypu po `HOPPER_RIM_Z` = 2,05 m, pak svislý lem,
`HOPPER_SLOPE_Z` zůstal jen jako spodek plnicího kvádru), pásnicové výztuhy a obruče, síto (nosné příčky a drátěná mříž), nohy se styčníky; šnek s vodorovným žlabem, kolenem a přírubami;
paluba z `SDT_DeckPlate` s odvodňovacími otvory. Uzly (`millOutletPort` v −1,03, `millPortCap`, plnicí a naftové uzly, kola, oj) a `i3dMappings` beze změny (XML se vyexportovalo shodně; šablona
`sdtLimeMill.xml.in` dostala ručně přidaný řádek `bagOutput`, který export dřív přepsal). Rozměry vozidla 2,51 × 4,817 × 2,554 m beze změny. Trojúhelníky vozidla 57 452 → 67 300.
Díly: `part_mill_mill` 2 640 → 4 052 (0,745 × 0,61 × 0,6 → 0,59 × 0,625 × 0,615, dřív do rozměru počítala trubka k cyklonu), `part_mill_bin` 2 584 → 7 140, `part_mill_hopper` 7 428 → 9 596,
`part_mill_auger` 2 256 → 3 656.

**Násypka na vápno** (`build_hopper.py`) se přestavovala jen nepřímo: sdílí motor a nádrž s pumpou (`part_engine`, `part_tank`), nová spojka Storz a štítky přímo na lievku a trubce; lievek, mříž
a podavač zůstávají jako dřív (priorita 2). Uzly a `i3dMappings` shodné.

Nepřeneseno: nádrž dronu (zbylý bod `_spolecne`), motor mlýnku (tlumič, filtr), blowPipe a koncovky hadic ve vlecích do jejich dalšího exportu. Ověřeno: stavba, srovnání XML a i3dMappings
s modem, `tools/lua_check.py`, `validate_mod.py` (tři známé chyby), `audit_spec_fields.py`, `check_xml_nodes.py`, snímky v GE (16 pohledů u prioritních položek, 8 u ostatních). Ve hře neověřeno.

## Tažný věšák Maxu a elektrocentrála podle reálných vzorů (2026-10-23; jen model a atlas nálepek, XML a Lua beze změny, ve hře neověřeno)

**Zadní tažný věšák** (`sdt_lime.build_rear_hitch`, díl `part_rear_hitch`): věšák visel ve vzduchu. Dvě krátké nožky se opíraly jen o spodní hranu zadního
nosníku (`RearBeam`, z 0,76), mezi nosníky rámu pod palubou ale žádný spodek není, nožky procházely držákem značky a tažná trubka vyčnívala přes půl metru bez
vzpěry k rámu; vzpěry končily u trubky bez styčníku a konzole zásuvky 13 pólů nebyla s trubkou spojená. Nově: dva příčníky 100 × 100 mm (`y_rear` −0,40…−0,30 a
−0,20…−0,10) přišroubované zespodu na spodní pásnice obou I-nosníků (`z_beam_bottom` = jejich spodní hrana 0,745, parametr se z Maxu předává jako
`DECK_TOP − DECK_PLATE − IBEAM_H`; osm šroubů se šestihrannou hlavou a podložkou), mezi nimi spojovací deska, pod nimi hlava věšáku 120 mm s tažnou trubkou,
trojúhelníkové žebro mezi hlavou a trubkou a dvě šikmé vzpěry (průměr 44 mm) od vnějších konců zadního příčníku k trubce s přivařenými styčnými plechy;
zásuvka 13 pólů je na rameni z boku trubky se žebrem. Konstrukce se vyhýbá držáku značky (`LicensePlateMount`, y 6,44–6,50) i podběhové
tyči (`Underrun_Bar`, y 6,05). **Koule zůstala na místě** (`0, 6,96, 0,58`, kloub `rearHitchJoint` se natočením 90° kolem Z a pozicí v `i3d` nezměnil, v XML Maxu
`attacherJoints` beze změny), takže sedí na kulovou spojku mlýnkového vozíku (`attacherJoint` mlýnku z 0,58, `attacherHeight` 0,58). Trojúhelníky věšáku 1 048 → 1 876.

**Elektrocentrála** (`sdt_generator.build_generator`, díl `part_generator`, všechny vleky): vzory Hyundai DHY8500SE (panel s displejem, klíčem, nouzovým STOP, žhavením,
12 V DC, zemněním a zásuvkami CEE s víčky; <https://www.mygenerator.com.au/assets/files/Hyundai_DHY6000SE_DHY8500SE_User_Manual.pdf>, s. 12–13), Kipor KDE6700TA (žlutý
kryt, modré zásuvky s odklopenými víčky, štítky LOW OIL; <https://www.vycepy.com/dieslova-elektrocentrala-kipor-kde-6700ta.html>), Heron 8896147 (panel zapuštěný
v trubkovém rámu, displej a zásuvky CEE; <https://www.elespo.cz/elektrocentrala-benzinova-17hp-8-2kw-10-25kva-400v-6-5kw-230v-podvozek-elektricky-start-img-8896147>),
Fogo FH 9000 TE (palivová nádrž nahoře, rám z tlustých trubek; <https://www.kvalitnikotle.cz/trifazova-elektrocentrala-fogo-fh9000te-8-7-kva/>) a Honda EG4500CX /
EG5500CX (vypínač motoru, voltmetr, jistič, zásuvky 230 V, DC svorky, zemnicí svorka, palivový kohout, víčko nádrže s ukazatelem;
<https://cf.hondappsv.com/files/OM/OM001398AUS/32Z306011_web.pdf>, s. 10–12).
- **Panel** (`decal_layout.GEN_PANEL`, `tools/make_decal_atlas.draw_gen_panel`, nálepka `genPanel` 480 × 280 mm, jedna na 1 mm): hlavička BZUK POWER, digitální displej
  V / Hz / provozní hodiny, klíč VYP–ZAP–START (klíč v poloze ZAP), červené nouzové STOP na žlutém lemu, kontrolky CHOD / OLEJ / NABÍJ., dvě zásuvky 230 V 16 A
  s odklopenými modrými víčky, zásuvka NABÍJEČKA (modrá CEE; u varianty se zadní průchodkou kabelu má stejný vzhled jen jako ozdoba), jistič 16 A, žhavení, výstup 12 V DC
  s víčkem, táhlo STOP MOTORU, mosazná zemnicí svorka, šrouby v rozích; popisky česky nebo piktogramy, oddělené oddíly. **Sytič** u dieselu není, nahradilo ho táhlo STOP
  motoru (reálné dieselové centrály ho mají); **palivový kohout** s červenou pákou a kalíkem je na boku nádrže pod stavoznakem.
- **Víčko nádrže**: příruba se čtyřmi šrouby, žebrovaná čepička, lanko, a na víku nádrže okénko ukazatele paliva se stupnicí (E červeně, F zeleně, ručička); stavoznak na boku
  zůstal. Horní hrana víčka (`result["cap"]`, `dieselNeckNode`) je ve stejné výšce.
- **Výfuk** s drátěným krytem tlumiče (čtyři podélné pruty a dva oblouky proti dotyku), **větrací mřížka** na střeše krytu.
- Zachováno: rozměry obalu, uzly `Gen_*_Frame / Body / Exhaust / ChargeSocket / Decals`, `generatorExhaust` (poloha i natočení), `dieselNeckNode`, zásuvka nabíječky v místě
  `SOCKET_LOCAL`, varianty `rear_socket`, jména v `i3dMappings`. Trojúhelníky: s bočním panelem (Middle, Mini) 5 651 → 7 023 (+24 %), s průchodkou kabelu (Max) 5 223 → 6 907 (+32 %).
- Atlas nálepek je sdílený: regenerovat `python tools/make_decal_atlas.py` a znovu exportovat všechny tři vleky (kopie `sdt_decals.dds` v Maxu a Mini se přebírají z Middle).

Export: Middle, Max i Mini (plné pečení vmask), XML všech tří vleků je proti předchozímu stavu **bajtově shodné** (včetně `i3dMappings`), počty uzlů shodné (Max 2 248,
Middle 1 517, Mini 839). Jediný další rozdíl proti staré i3d jsou materiály `SDT_AluCast` a `SDT_HoseSpiral` v Middle a Maxu: pocházejí z rozpracované přestavby čerpadla
a hadic (jiný úkol, `sdt_tanks.py`), ne z této změny. Ve hře ověřit: zapřažení mlýnkového vozíku za Max (výška a poloha oka na kouli), držák značky u věšáku, vzhled panelu a
čitelnost popisků z hráčovy vzdálenosti, kouř z výfuku (`generatorExhaust` se nepohnul), zásuvka nabíječky na Middle a Mini.

Snímky před/po z GE: `out/centrala_hak/srovnani_centrala.jpg`, `srovnani_centrala_panel_zblizka.jpg`, `srovnani_hak.jpg`, `srovnani_hak_bok_zezadu.jpg` (zdroje v `out/centrala_hak/ge`; stav
„před“ je kopie dílů a Maxu z `tmp/centrala_hak/before`). Katalog (karty `part_generator`, `part_rear_hitch`, Max, Middle, Mini) je přegenerovaný a nasazený
(`/static/sdt-katalog/`, položky `part_generator` a `part_rear_hitch` v `tools/katalog_analyza.json` jsou ve stavu „opraveno“).

## Úpravy 2026-10-28 (po poznámkách Pavla; Lua, XML a modely hotové, ve hře neověřeno)

- **Mlýnek, výstup ze sedadla:** ventil výstupu (hadice / roura) jde přepnout i po nastoupení do vozíku klávesou Y (`IMPLEMENT_EXTRA3`, `SprayDroneMill.actionEventOutput`, text podle stavu);
  pěšky levé tlačítko myši na páku ventilu. Od 2026-10-29 jde přepnout i s připojenou hadicí (ta pak nic nedostane), výsypná roura O, viz „Big bag z mlýnku“.
- **Big bag jemného vápna:** vlastní potisk místo vanilla vzoru vápna, aby šel poznat od obyčejného vápna. Texturu staví `blender/limebigbag_label.py` (štítek jako na pytli: BZUK, VÁPNO, „jemně mleté vápno“,
  zelený rám a dva zelené pruhy; UV vanilla vaku zjištěné importem i3d) do `objects/limeBigBag/textures/limebigbag_diffuse.dds`; nasazuje ji `SprayDroneHopper.applyBigBagLabel`
  (připojené za `FillUnit.onLoad`): vymění difuzní texturu materiálu uzlu `lime_mat`, ze kterého si vak vzhled kopíruje. Záznam `fillTypeMaterials` s `materialSlotName` nešel
  (2026-10-29: vanilla vak nemá pojmenované sloty, hra hlásila „Material for slot name 'bigBagLime_mat' not found" a vak zůstal s vanilla vápnem). Obrázek do obchodu `store_limeBigBag.dds` je render vaku s potiskem.
- **Hadice jen přes R:** levé tlačítko myši už hadici nebere, nepřipojuje ani neodpojuje (`SprayDroneWaterHoseActivatable:onClick`), dělá jen přepnutí režimu vstupu pumpy (ventil vstupu na koncentrát se otevírá sám).
- **Koncovka hadice** (`sdt_mlyn._hose_end`, použitá u pumpy, Middle a Maxu): pryč plochý válcový pahýl, který z koncovky trčel; gumová ochrana ohybu se zužuje na poloměr hadice (0,032 m)
  a končí v 0,215 m, články hadice vedou od čela spojky, takže se v ní skryjí.
- **Relé tyč:** nenastupuje se do ní (v `modDesc.xml` pryč `enterable` z typu `sdtRelayPole`, v `relayPole.xml` pryč `<enterable>` a `<input>`, ze Lua `getIsEnterable`, `getDistanceToNode`, klávesa ve vozidle).
  Rozložení / složení R a zapnutí / vypnutí **B zvenku** (`SprayDroneRelayActivatable`, akce `SDT_TOGGLE_FOOT`, jen u rozložené tyče). Baterie tyče se ukazuje jako elektřina (`unitTextOverride="$l10n_unit_kw"`),
  ne jako litry. Nabíjení vanilla stanicí přes LoadTrigger (R u stanice) zůstává, nastupovat se k tomu už nedá.
- **Cisterna (vráceno):** výstup pumpy na libovolnou cizí nádrž i omezení na pojmenované ventily jsem zase odebral; hadice zdroje bez nízkého vypouštěcího uzlu (cisterna MAN TGS z `FS25_lsfmUniversalTankPack`
  má uzel nahoře) se připojuje kamkoli na karoserii jako dřív, ale jen ke zdroji, který obsahuje vodu (u prázdné nádrže HUD řekne `sdt_wh_tankEmpty`). Při puštění hadice se do logu zapíše okolí (`describeSurroundings`).
  Hadice teď u koncovek vede ~0,26 m (`HOSE_STIFF`) vodorovně ve výšce spojky, teprve potom klesá, aby nevylézala pod gumovou ochranou ohybu bokem.
- **Kolize Middle (podlaha):** staticky v pořádku (`colChassis` pokrývá celou palubu, stejné atributy jako u Maxu, i3d shodné s dřívějším exportem). Příčina se musí změřit ve hře (`colMap` / `colProbe`);
  podezřelé je načtení uloženého rozloženého vleku: `SprayDroneStation.updateFreeze` v tom případě tvary nevrací (`loadedFrozen`).

### Drony jako předměty (2026-10-28; napsáno, ve hře neověřeno)

Vlek se prodává bez dronu. Drony S / M / L (postřikové) a K (skenovací) se kupují zvlášť v obchodě (BZUK, vybavení), nosí se v rukou a R u plošiny vleku se nasadí; R bez dronu v ruce
u obsazené plošiny ho odepne (mimo misi; rozložený se nejdřív složí a předmět pak zůstane ležet přesně tam, kde dron stál). Dron nese svou náplň. Baterie dronu se při sundání vrátí do nabíječky vleku. Podrobnosti: `docs/NAVRH-dron-predmet.md`, kap. 12.

## Hadice do cizích nádrží a rybníka (2026-10-28, ověřeno ve hře simulací i skutečnými stisky R)

- Výstup pumpy jde kromě vodních ventilů vleků připojit na libovolnou nádrž, která bere vodu a má místo (cisterna, IBC, postřikovač): `SprayDroneWaterHose.findSinkAt` má zálohu
  se `snapToBody`, hadice nese `targetPort = TANK_ARG` (14), přenos dělá `getWaterSinkUnit` + `transfer` v `updateServer`, text `sdt_wh_connectTank`.
- Hadice vleku (ventil na nádrži) jde připojit i k prázdné cizí nádrži: `findSourceAt` vrací 7. hodnotu `push`, `targetPort = TANK_ARG` a voda teče z vleku do ní.
  Z nádrže s vodou se dál čerpá do vleku. Vstupní hadice pumpy zůstává jen na zdroje s vodou.
- `SINK_RADIUS` 2,0 m (ventily vleku jsou na palubě, hráč stojí na zemi u boku). Koš hadice pumpy hledá vodu v okruhu `POND_REACH` 1,5 m kolem ruky.
- Při puštění hadice se do logu zapisují ventily okolních vozidel (druh, vzdálenost, skrytý) a u pumpy hloubka vody pod koncem hadice (`describeSurroundings`).
- Výstup mlýnku: uzel `millOutletPort` leží na čele spojky (dřív 3 cm před ní, koncovka hadice visela s mezerou).
- Koncovka hadice (`sdt_mlyn._hose_end`) nemá pevnou gumovou ochranu ohybu; hadice pumpy je modrá (vstup) a červená (výstup).
- Mini: držák tyče posunutý dopředu (y −2,95 až −1,50), displej v pravém zadním rohu paluby.

### Dusík a pH z Precision Farming ve skenu (2026-10-29, krok 1–2; NEOTESTOVÁNO ve hře)

Sken čte u každé buňky i mapy PF (`SprayDroneScanMap.readPF`): dusík kg N/ha a pH, jen když je PF ve hře (`SprayDroneStation.getPrecisionFarming`). Průměr vnitřní hodnoty
ve čtverci buňky (`DensityMapModifier:executeGet()` bez filtru = součet / počet pixelů) se převede `getNitrogenValueFromInternalValue` / `getPhValueFromInternalValue` (lineárně mezi
sousedními stavy). Hodnota je v `map.pf[index]` zvlášť od zabalené hodnoty buňky (ta je plná, 28 bitů): `1 + dusík (0..511) + pH × 10 (0..127) × 512`, 17 bitů v `SprayDroneScanEvent`
(`cell[6]`), v savu `<pf>index:hodnota …</pf>` u mapy. `treatCell` ji po aplikaci přečte znovu. `SprayDroneScanMap.unpack(map, index)` vrací buňku s `nitrogen` a `ph`.
Plánovač: vrstvy „Dusík (PF)“ a „pH (PF)“ (5 tříd, hranice `SprayDroneScanOverlay.NITROGEN_STEPS` 40/80/120/160 kg/ha a `PH_STEPS` 5,5/6/6,5/7 jsou odhad – po prvním skenu je nutné
srovnat s hodnotami `SDT SOIL` ze `soilProbe`), řádek „Půda (PF)“ v kartě mapy pole. Souhrn (`getSummary`): `pfCells`, `avgNitrogen`, `min/maxNitrogen`, `avgPh`, `min/maxPh`.
**Ověřit:** že `executeGet()` bez filtru vrací součet hodnot (jinak `readPFAverage` vrátí nesmysl), skutečné rozsahy N a pH na mapě, multiplayer (nový bit v eventu).
Krok 3 (aplikace vápna a hnojiva podle pH a dusíku) a zápis do PF mapy vzorků zatím není.

**Ověřeno ve hře (2026-10-29, slot 11, pole 23, Max se skenovacím dronem):** `executeGet()` bez filtru vrací součet hodnot (průměr 6,0 = 25 kg N/ha, 15,0 = pH 6,3, 14,48 = pH 6,2 sedí s histogramem),
sken: 138 buněk, dusík Ø 32 kg/ha (25–35), pH Ø 6,3 (6,1–6,4). PF se dřív nenašlo, protože `_G` v modech má metatabulku a `rawget(_G, "FS25_precisionFarming")` vrací nil;
`SprayDroneStation.getModEnv` bere `_G[jméno]`. Rozsahy PF: dusík 0–220 kg/ha (45 stavů po 5 kg, `nitrogenMap.amountPerState`), pH 4,50–8,25 (31 stavů po 0,125).
**Krok 3 (aplikace podle PF, ve hře ověřen jen výběr buněk, ne let s přípravkem):** `SprayDroneScanMap.getTargetNitrogen` bere cílový dusík z `nitrogenMap.fruitTypeIndexToFruitRequirement[plodina].averageTargetLevel`
× `amountPerState` (pole 23, plodina 24: cíl 65 kg/ha) a ukládá ho do `map.pf` (23 bitů). `getSpotSelector`: vápno = pH < `PF_PH_TARGET` 6,5 − `PF_PH_TOLERANCE` 0,25, hnojivo = dusík < cíl − `PF_NITROGEN_TOLERANCE` 10 kg,
bez PF dosavadní vanilla úrovně. Na poli 23: vápno 38 z 138 buněk, hnojivo 138 z 138. Cíl pH je pevných 6,5 (PF `getOptimalPHValueForSoilTypeIndex` vracel 0, půdní typ 0 – před odkrytím půdy PF nejspíš nevrací nic).
Ladění: `scanFly`, `scanPfInfo` (souhrn, výběr vápna/hnojiva/herbicidu, srovnání buněk s histogramem), `pfApi`, `pfTarget`, `scanLayerNitrogen/Ph`.
Offline zkouška logiky PF (kódování `encodePF`/`decodePF`, `readPF` s falešnou mapou, cílový dusík, souhrn, `getSpotSelector`): `python tools/test_pf.py` (je i v `check_all.py`). Ve hře zbývá let s přípravkem, vrstva pH, multiplayer.

## Přenosný skenovací dron (kufr) (2026-10-29, F2 z `docs/PLAN-airasi-kufr.md`; Lua a XML hotové, NEOTESTOVÁNO ve hře)

**Co to je.** Sada v obchodě (kategorie Drony, 9 750 €): kufr `objects/droneCase/scanCase.xml` (vehicle type `sdtDroneCase` = pallet + `foldable` +
`sprayDroneStation`), v něm dron `C` (třída Mavic 3M, `scan="true"`) a dvě baterie. Model a strom uzlů: `docs/NAVRH-kufr-modely.md`.
Skenovací dron `K` na vlecích zanikl (D2): předmět `droneK.xml` je jen skrytý v obchodě (staré savy se načtou), plošina vleku skenovací variantu
odmítne (`getPadsProblem`: `scan` jen u `portable`), bloky K v šablonách `blender/templates/*.xml.in` jsou zkrácené na pahýl, který jen schová
`Drone_K_Root`, dokud ho staví build skripty (až z nich K zmizí, smazat i pahýly).

**Jak funguje** (`scripts/SprayDroneCase.lua`, profil `sprayDrone#portable`):
- Víko = Foldable (`caseLidAnim`, čas 0 otevřeno / 1 zavřeno, 5 s; AIRASI 6 s). Otevření (Pavel 2026-10-29: dron nesmí startovat z kufru):
  víko → z pěny víka se vyndá složená přistávací podložka `casePad`, položí se na zem vedle kufru (strana −X, Ø 0,9 m / AIRASI 1,4 m) a
  rozevře → nosič `droneCarrier` přenese dron z pěny na střed H → teprve pak se rozloží ramena (`trailerFoldEnd` 0,2). Zavření obráceně.
  Sekvenci a čísla dává `blender/build_drone_case.py` (`docs/NAVRH-kufr-modely.md`, „Animace víka“).
  Otevírá a zavírá se pěšky R u kufru (`SprayDroneCaseActivatable`); zavřít jde jen s dronem doma a dotočenými vrtulemi (`getIsFoldAllowed`).
  Když hráč míří na baterii nebo u ní stojí do 0,6 m, R místo víka vyndá baterii (sekce Ovládání).
- Domov dronu = střed podložky: `getHomePosition` bere kořen dronu, za letu rodiče kořene (`droneCarrier`) s `localTrans`, takže jde s animací
  sám; vzlet i kontrola volna (`getTakeoffClearance`) počítají z podložky. Změna víka přepočítá plán (`SprayDroneCase.updateVisuals` →
  `markRouteDirty`). Tablet kufr najde jako každý vlek (`SprayDroneLink.collectTrailers` bere každé vozidlo se spec stanice). Mise je jen sken,
  v plánovači chybí „aplikace podle skenu“ (`SETTINGS.applyMode.sprayOnly`), řádky nádrže, nafty a centrály.
- Bez Enterable (`prerequisitesPresent`), bez bedny (`SprayDroneToolbox`), bez slotu dronu jako předmětu (`SprayDronePadSlots`), bez zmrazení.
  **Otevřený kufr nejde zvednout** (Pavel 2026-10-29, `SprayDroneCase.loadPickUpLock` obaluje `getCanBePickedUp`; víko otevřené nebo v pohybu =
  `getIsClosed` false), nápověda u kufru „Kufr jde zvednout až zavřený“. Na korbu se bez zvednutí nedostane; fyzika se nezamyká (kinematický
  kufr by na korbě jedoucího auta visel ve vzduchu), takže vozidlem jde otevřený kufr odtlačit – pak zabere MOVE_TOLERANCE. Pohyb kufru za letu (rychlost nad `MAX_TRAILER_SPEED`, nebo posun víc než `SprayDroneCase.MOVE_TOLERANCE` 2 m
  od místa vzletu) přeruší misi jako pohyb vleku (`STATUS_TRAILER_MOVED`).
- **Nabíjení (D1)**: baterie (pool `spec.batteries`, `power#slots="2" batteries="2"`: šachty `caseBatterySlot`, `caseBatterySlot2`; strop poolu
  je i s baterií v dronu, takže dron + jedna náhradní a po přistání je kam vrátit vybitou – servis ji vymění za nabitou jako u vleku) se nabíjí jen u zdroje do `CHARGE_RANGE` 15 m:
  vlastní budova farmy (placeable farmy s `spec_farmhouse/workshop/husbandry/productionPoint/silo/objectStorage/greenhouse/chargingStation`,
  nebo s krytými plochami `indoorAreas`; vzdálenost od kryté plochy, jinak od kořene) – nebo běžící centrála vleku SprayDrone
  (`getHasPower`), která pak pálí naftu jako za jednu nabíjenou baterii (`caseLoads`, `getNumCaseLoads`). Rychlost = nabíječka vleku
  (`power#chargeMinutes` 10). Nabíjí se baterie v obou šachtách i v dronu, který sedí v kufru. Bez zdroje: plán hlásí „nemá zdroj nabíjení“,
  mise skončí `STATUS_NO_CHARGE`. Zdroj jde klientům ve stavu vozidla (2 bity). U kufru pěšky nápověda ukáže baterii, zdroj a stav dronu;
  kabel `caseChargeCable` je vidět při nabíjení, LED `caseChargeLed0..3` = průměrné nabití všech baterií po čtvrtinách (horní bliká při nabíjení).

**Realistický sken (F2)**: sken nečte vápno ani pH (pozice v zabalené hodnotě a v `map.pf` zůstávají kvůli starým mapám, nečtou se);
vitalita (`sprayLevel`) a dusík PF jen nad plodinou, kameny jen na holé půdě. Vrstvy plánovače: bez „Vápno“ a „pH (PF)“, „Hnojení“ je
„Vitalita porostu“ (nová třída „bez porostu“). **Vápnění podle skenu** (`getSpotSelector`, selektor dostává `map, index`): s PF jen buňky,
kde farma odebrala vzorky (`coverMap:getIsUncoveredAtPos`, zkouší `(x, z, farmId)` a pak `(x, z)`, chyba = bez vzorku), pH se čte živě z
`pf.pHMap` přes čtverec buňky; bez vzorku se nevápní. Bez PF rozhoduje vanilla úroveň vápna přímo z pole teď (`getLiveLimeLevel`) – vanilla vzorky
nemá a stav vápna ukazuje i herní mapa, takže to není informace „ze skenu“.

**Ověření offline:** `python tools/test_case.py` (budovy, zdroj, nabíjení, zátěž centrály, plán, odmítnutí K na vleku), `python tools/test_pf.py`
(sken bez pH, dusík jen s plodinou, vápno jen se vzorkem, bez PF vanilla vápno; mutace tolerancí ji shodí), obojí v `check_all.py`.
**Ladění** (`SprayDroneDebug`, cílí na nejbližší kufr k hráči): `caseInfo` (víko, baterie, zdroj, nejbližší budova a centrála se vzdáleností),
`caseOpen` / `caseClose`, `caseCharge` (100 %), `caseEmpty` (30 %). Příkazy zpracuje první aktivní vozidlo se stanicí (s `targetMax` jen Max).
**Ve hře ověřit:** koupě, kufr na zemi; R otevřít/zavřít (podložka, přenos dronu, ramena až na podložce, vrtule), zavřít s dronem venku odmítnuto; tablet najde kufr, sken pole a návrat;
domovská orientace (dron v kufru otočený o 90°, `initHomeYawOffset`); kufr u farmhouse/kůlny nabíjí, u plotu ne, u Maxu se zapnutou centrálou
nabíjí a Max pálí naftu; mise s vybitou baterií bez zdroje skončí hláškou; otevřený kufr nejde zvednout (nápověda), odtlačení za letu misi přeruší; uložení a načtení; vrtule
přesahují kufr při rozložení (kolize modelu se stěnami se neřeší).

## Vzorkovací dron AIRASI (kufr) (2026-10-29, F3 z `docs/PLAN-airasi-kufr.md`; Lua a XML hotové, NEOTESTOVÁNO ve hře)

**Co to je.** Sada v obchodě (kategorie Drony, 14 600 €, jen s Precision Farming – rozhodnutí D5): kufr `objects/droneCase/samplerCase.xml`
(týž typ `sdtDroneCase` a profil `portable` jako skenovací kufr), dron `P` (`drone#sampler="true"`, blok `<sampler>`), dvě baterie a bednička na
8 vzorků. Kufr na dvě poloviny: víko se otevře o 180° (pant v půlce výšky za zadní stěnou) a leží vnitřkem nahoru na zemi
za kufrem; v něm bednička (`caseSampleBox`, otočený o 180° vůči víku) a složená podložka (uložená lícem dolů, takže po otevření leží lícem
nahoru a při vyndání se neotáčí: zvedne se nad kufr, přenese vedle (−X) a spustí). Dron P má vysoké skládací nohy `Drone_P_Leg_1..4`
(foldPart kolem X, 0,6–1 rozložení) a trup se s nimi zvedne (`foldPart` s `foldedTrans`/`unfoldedTrans` na `Drone_P_Tilt`, +0,395 m;
trup ~0,5 m nad zemí); chodidla jsou v rovině kořene. Bez PF je položka v obchodě skrytá (`SprayDroneStoreCategories.hidePFItems`: `showInStore = false` po `StoreManager.loadMapData`
i v `loadMap`; PF se pozná podle `g_modIsLoaded["FS25_precisionFarming"]`) a kufr misi odmítne (`sdt_sampler_noPF`, status `STATUS_NO_PF`).

**Model od 2026-10-29 (v3, platí místo popisu výš):** kufr 1,15 × 0,75 × **0,55 m** (`CASES.samplerCase.crate_lid`). Víko je v `caseLidAnim`
(6 s): po celou dobu rozložení (i za letu) leží otevřené o 180° za kufrem a bedna je vidět; při složení (R) se nejdřív uklidí dron do pěny a
podložka do štěrbiny pod bednou, **teprve pak se víko zavře** (4,92–6,0 s, −180° → 0°), při otevírání se víko otevře jako první. Zavřený (složený)
kufr = zavřené víko = jde zvednout; i3d má víko zavřené, takže koupě a savy se složeným kufrem jsou zavřené. (v2 z téhož dne mělo víko trvale
otevřené – Pavel tím myslel „při práci“.) Celé víko vyplňuje bedna 1,06 × 0,66 m bez vlastního víčka s mřížkou 6 × 4 = **24 přihrádek**
(`boxCapacity="24"`), krabička 0,12 × 0,095 × 0,09 m; zavřená bedna visí krabičkami dolů nad dronem: kvůli tomu je kufr o 5 cm vyšší (víko 0,25 m,
pant `hinge_z` 0,278), vůle krabiček nad nejvyšším místem dronu (náboj motoru) **21 mm**, víko projde celým otáčením bez dotyku dronu a baterií
(`crate_lid_report` v exportu, hlídá `tools/test_case_lid.py`). Kolize jen zavřeného tvaru (`floorCollision01`), otevřené víko je bez kolize jako
u skenovacího kufru (pevný tvar za kufrem by u zavřeného trčel ven). Těžiště zavřeného kufru `0 0.28 0.02`. Na bednu se jako na „odeslat vzorky“
míří jen u otevřeného / otevírajícího se kufru (`isAimedAtBox`), jinak by zavřený kufr nešel zvednout. Dron nese 2 krabičky za sebou pod trupem
(mezi pouzdrem sondy a zádí). Scan kufr se nemění.

**Jak funguje** (`scripts/SprayDroneSamples.lua`; ve `SprayDroneStation` jen háčky):
- Vzorkovač má `missionMode` 1 (bez nádrže, plnění a postřiku jako sken), ale `getIsScanMode` ho za sken nebere: počasí jako postřik
  (`sprayMaxWind` 10 m/s varianty, déšť), tma nevadí. Jen vlastní pole (`sdt_warning_samplerOwnOnly`). Volby druhu mise plánovač nemá.
- **Body**: mřížka uvnitř polygonu pole, rozestup `sqrt(10000 / soilMap:getNumSoilSamplesPerHa())` (≈ 43,9 m při 5,2/ha), středy čtverců
  světové mřížky (stejné body při každém výpočtu); malé pole = jeden bod v těžišti. Bod je hotový podle mapy pokrytí PF (`coverMap.bitVectorMap`
  přes `getBitVectorMapPoint`: `sampledValue` 8 = odebráno, čeká na laboratoř; 2..`maxValue` 7 = odkryto; bez mapy `getIsUncoveredAtPos`).
  Vlastní evidence bodů ani event nejsou potřeba – stav drží PF (a synchronizuje ho). Body dál než dosah se počítají „mimo dosah“.
  Bod, kde odběr neprošel (cizí pozemek, PF pixel mimo pole), se do konce hry přeskakuje (`samplerSkip`, neukládá se).
- **Dávka** (`SprayDroneSamples.startNextBatch` místo `startNextBatch` po kontrole pole a počasí): nejvýš `sampler#capacity` (2) bodů a nejvýš
  místo v bedničce; nejbližší k domovu, pak nejbližší k předchozímu. Waypointy: přelet `getTransit` (výška `sprayHeight` 4 m nad bodem), nad bodem
  sestup na `sampler#height` (kořen dronu = chodidla nad terénem, 0,02 = stojí na nohách), waypoint `sample = true`, výstup, mezi body nad překážkou
  (`getHopHeight`), domů `getTransit` s přistáním. Spotřeba = `pathCost` + výdrž (`holdTime` + 2 × `probeTime`) × vznášení + rezerva; když
  nestačí baterie, zkusí se méně bodů, pak výměna / nabití jako u postřiku (`swapBattery`, bez zdroje `STATUS_NO_CHARGE`), a když nestačí ani
  plná baterie na jeden bod, `STATUS_UNREACHABLE`.
- **Odběr** (`updateFlight`: po dosažení waypointu `sample` `startHold`, pak `updateHold` po kontrolách baterie, počasí a signálu): výsun sondy
  (`probeTime` 1,6 s; čtyřstupňová: `Drone_P_Probe` `probeTravel` 0,18, `ProbeMid` a `ProbeMid2` `midTravel` 0,18, `ProbeTip` `tipTravel` 0,19 m
  po Y, dohromady 0,73 m; hrot z výšky trupu na nohách ~0,31 m pod terén; pouzdro jde trupem nahoru jako stožárek), výdrž (`holdTime` 3 s), na serveru odběr
  (`DensityMapCircle:updateFromWorldPosition(x, z, 32.5, 20)` + `coverMap:analyseArea(kruh, nil, farmId, farmlandId)`, poloměr jako ISARIA;
  pozemek jen vlastní / přístupný jako PF `SoilSampler`; statistika pozemku `numSoilSamples` / `soilSampleCosts`), zasunutí, `Drone_P_Sample1/2`
  viditelné podle vzorků v dronu. Návrat domů za výdrže sondu zasune.
- **Bednička**: po přistání jdou vzorky z dronu do bedničky (`onLanded`), `caseSample1..8` viditelné podle počtu, víčko `caseSampleBoxLid`
  se po změně počtu na 3 s otevře (−100° kolem X). Plná bednička další misi nespustí (`sdt_sampler_boxFull`, status `STATUS_BOX_FULL`).
  V savu `sprayDroneStation#samples` (i vzorky, které byly při uložení v dronu); klientům ve stavu vozidla (počet v bedničce 4 b, v dronu 2 b,
  sonda 1 b, za zdrojem nabíjení kufru).
- **Odeslání**: pěšky u kufru levé tlačítko s pohledem na bedničku (uzel `caseSamples`, 0,3 m; text „Odeslat vzorky (n)“ jen při míření;
  přidaná k activatable kufru obalením `SprayDroneCaseActivatable`, protože systém activatable ukazuje jen jeden; kufr se při míření na
  bedničku nedá zvednout, `getCanBePickedUp`), nebo tlačítko „Odeslat vzorky“ v plánovači (místo „Pole od začátku“, klávesa End). Příkaz `SprayDroneCommandEvent.SEND_SAMPLES` → server `soilMap:analyseSoilSamples(farmId, n)`, bednička prázdná; klient
  ukáže hlášku s počtem a cenou (n × `getPricePerSoilSample`, účtuje PF po rozboru, 5 s herního času na vzorek).
- **Plánovač**: dlaždice „Body zbývá / celkem“ a „Bednička“, blok body / odebráno / zbývá / mimo dosah, vzorky v dronu a v bedničce, laboratoř PF
  (v rozboru) a cena za vzorek; na mapě body (odebrané zeleně, čekající oranžově, mimo dosah šedě). Dávky a čas: prvních 12 dávek skutečnými
  přelety, zbytek odhadem. Statusy konce mise vzorkovače jsou 28–30 (konec rozsahu 5 bitů, ať se nepotkají s dalšími statusy stanice).

**Ověření offline:** `python tools/test_samples.py` (v `check_all.py`): mřížka a hustota, světová síť, malé pole, stav bodu z mapy PF, body k odběru
a mimo dosah, pořadí a velikost dávky (kapacita, místo v bedničce i se vzorky v dronu), waypointy a zmenšení dávky podle baterie, odběr na vlastním a
cizím pozemku, výsun / výdrž / zasunutí sondy, přistání, odeslání, důvody konce mise; mutace kontroly bedničky a stavu PF ho shodí.
**Ladění** (`SprayDroneDebug`, cílí na nejbližší vzorkovací kufr): `samplerSpawn` (kufr 15 m od hráče), `samplerFly` (1. volání otevře víko a vybere
pole 23 nebo nejbližší vlastní, další spočte náhled a spustí misi), `samplerInfo` (body, odebráno, zbývá, mimo dosah, dron, bednička, laboratoř PF,
dávky, sonda, status), `samplerSend`, `samplerBoxFull` (bednička plná), `samplerPlanner` (plánovač jako z tabletu).
**Ve hře ověřit:** obchod bez PF (položka skrytá) a s PF; koupě, R víko, klik na bedničku odeslat; let k bodu, sestup na zem, sonda pod povrch (ne nad zemí), odběr
v PF mapě (oblast „odebráno“), vzorkovnice v dronu a pak v bedničce, víčko; druhý bod a návrat; plná bednička → hláška; odeslání → PF laboratoř
a platba po rozboru; uložení a načtení (počet v bedničce); domovská orientace dronu P v kufru; podložka 1,4 m (víko 180°, podložka z víka přes kufr na −X), přenos dronu, nohy se rozloží až na podložce a trup se zvedne (na podložce sonda zasunutá); bednička ve víku; multiplayer (sonda, bednička, odeslání z klienta). **v3:** R zavře víko až po uklizení dronu a podložky, zavřený kufr
jde zvednout (i s pohledem na víko), otevřený ne; po koupi a po načtení složeného kufru je víko zavřené, rozloženého otevřené; zavřený kufr
na korbě (těžiště, nepřevrací se); přes ležící otevřené víko se prochází (bez kolize).

## Směrová relé tyč (2026-10-29, místo antén na stativu; NEOTESTOVÁNO ve hře)

**Dosah kufrů.** Rádio kufru je menší než u vleku: `sprayDrone#maxRange` (i `drone#maxRange`) sken 500 m, AIRASI 400 m. Pole mimo dosah se
objede (kufr se přenese blíž), nebo se dosah prodlouží relé tyčí – všesměrovou, nebo směrovou. Antény na stativu (`objects/antenna`, párování
se stanicí kabelem) jsou zrušené; antény z konfigurace vleku v obchodě zůstávají.

**Předmět** `objects/relay/relayPoleDirectional.xml` (obchod Vybavení, 900 €, silná +450 €): kopie relé tyče (`sdtRelayPole`, `SprayDroneRelay`:
stejná trojnožka, R rozložit / složit, B zapnout / vypnout, baterie 5 h, nabíjení na vleku i u nabíjecí stanice, držák tyčí na vleku), jen na
teleskopu nese místo radomu **panel** (tvar z dřívější směrové antény). Čelo panelu = osa +Z předmětu, poznat podle širokého žlutého pruhu nahoře
na čele (záda tmavá). `sprayDroneRelay#sectorAngle="99"` a `#sectorFactor="1.75"`.

**Signál**: tyč pokrývá **jen výseč** 99° kolem osy +Z s dosahem poloměr × 1,75 (standard 300 → 525 m, silná 400 → 700 m); za tyčí, do stran
ani těsně kolem sebe nic. Spojení tyče se stanicí jako u všesměrové: tyč musí stát v rádiu stanice. Natáčí se položením: složenou postavit čelem
k poli a rozložit (rozložená je kinematická; ladicí `relayRotate`).

**Logika** (`SprayDroneLink`): tyče se poznají podle souboru (`RELAY_FILES`, `isRelayPole`). Oblast tyče je `{x, z, r, radius, sectors}`
z `getRelayShape` (všesměrová kruh `r = radius`, směrová `r = 0` + jedna výseč), ve hře `getRelayEntry` (poloha, síla, `getRelaySector`,
natočení `getRelayDirection`). Bod v oblasti `isInShape` (stará `{x, z, radius}` fungují dál). Používá ji `getActiveRelays` / `getRelays`,
`getSignalCircles` (obrys v plánovači i ve světě: `getCoverageLines` kreslí u směrové jen oblouk a boky výseče, kruh `r = 0` vynechá),
`isConnected`, `getNeededRelays`, `isRelayNeeded` a `getRelayBlockReason` (pojistky složení / vypnutí a výdrž baterie před dávkou platí
pro obě tyče stejně). `getRangeBonus` (strop dosahu z baterie = rádio + bonus) bere vzdálenost tyče, a když tyč sahá dál než rádio stanice,
i ten rozdíl. Rádio stanice je teď vždy kruh (`getRadio`).

**Držák na vleku** (`SprayDroneRelaySlots.POLE_FILES`): bere obě tyče, slot si pamatuje druh (`#kind` v savu, 2 bity po síti) a vyndá
tutéž tyč; maketa v držáku je pro oba druhy stejná.

**Model**: `blender/build_link_items.py -- relayDir` (stativ, skříňka a baterie jako u tyče, `panel_parts`; složený panel má vlastní kolizi
`panelCollision`), náhledy do `tmp/relayDir/`. Build všesměrové tyče a tabletu se nezměnil (ověřeno: stejné i3d i XML).

**Ověření offline:** `python tools/test_relay_sector.py` (v `check_all.py`): výseč bez kruhu, hranice úhlu 49,5°, přechod ±180°, standard
a silná, obrys, `isConnected` / `getSignalCircles` / `getNeededRelays` / `isRelayNeeded` / pojistka `getRelayBlockReason` se směrovou tyčí,
`getRangeBonus`, soubory tyčí a držák (`getPoleKind`).
**Ladění** (`SprayDroneDebug.ENABLED`): `relaySpawn dir` (složená 2 m před hráčem čelem po směru pohledu), `relaySpawn` (všesměrová),
`relayAct` (proč tyč nenabízí R, druh), `relayInfo` (tyče do 2 km: druh, síla, azimut čela, oblast, aktivní, v rádiu stanice, pojistka;
nejbližší stanice a pole), `relayRotate <stupně>` (nejbližší tyč; rozloženou nejdřív složit).
**Ve hře ověřit:** obchod (obrázek, cena, konfigurace síly 525 / 700 m), R / B, kontrolka a prstenec pod panelem, složený panel nekoliduje,
plánovač kreslí výseč na správnou stranu (čelem panelu), dron ve výseči letí, za tyčí ne; pojistka složení za letu; držák na vleku (uložit,
vyndat, zůstane směrová); uložení / načtení, MP.

