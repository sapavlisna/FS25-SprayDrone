# Dron: jak má fungovat (zadání pro implementaci letu)

Popisuje chování postřikového dronu u malého servisního vleku `FS25_SprayDroneTrailer`
(`mod/FS25_SprayDroneTrailer`). Co je hotové a co se teprve staví, je v sekci **Stav**.

## Scénář hráče

1. Hráč přiveze vlek autem k poli a zastaví. Vlek zůstane zapřažený, nebo ho odpojí.
2. Rozloží vlek (klávesa skládání, výchozí `X`). Tím se vysune žebřík a pak se na plošině rozloží dron
   (ramena, pak listy). Při složení vleku se dron složí jako první (listy, pak ramena), potom žebřík.
3. Nastoupí do vleku (`E` u vleku, nebo `Tab`). Do složeného vleku nastoupit nejde.
   Je to stanoviště pilota: kamera kolem vleku, žádné řízení jízdy.
4. Kolem vleku je ve světě vidět **kruh dosahu** dronu (poloměr `range`, výchozí 300 m).
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
8. Na vleku přistane, čerpadlem se postupně doplní nádrž z nádrže vleku (hnojivo nebo herbicid, podle toho, co ve
   vleku je) a když je baterie pod 30 %, vymění ji za nejnabitější náhradní; vybitou nabíjí elektrocentrála na naftu.
   Když žádná náhradní není nabitá, dron čeká. Pak letí na další dávku. Opakuje se, dokud není pole hotové.
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

Dron je součástí vozidla vleku, pod uzlem `droneRoot` v `sprayDroneTrailerCar.i3d`. Na plošině sedí
uprostřed (střed trupu = střed plošiny), nosem po směru jízdy; v i3d má složená ramena i listy:

| i3dMapping | co to je |
|---|---|
| `droneRoot` | kořen dronu. Počátek je uprostřed pod lyžinami, stojí na horní plošině. Za letu nese polohu a yaw. |
| `Drone_A_Tilt` | náklon za letu (pitch/roll), 0,55 m nad lyžinami; pod ním všechny díly |
| `Drone_A_ArmPivot_1..4` | kloub ramene (otáčí se kolem svislé osy) |
| `Drone_A_Rotor_<i>Top/Bottom` | vrtule (souosé páry), točí se kolem svislé osy; pod ní dva listy |
| `Drone_A_Blade_<i><Top/Bottom><0/1>` | list vrtule, počátek ve středu náboje (skládá se kolem něj) |
| `sprayDroneTrailerCar_main_component1` | fyzikální komponenta vleku (enterReferenceNode) |
| `outdoorCamera`, `outdoorCameraTarget` | kamera pilota, otočná kolem plošiny |
| `exitPoint` | kam hráč vystoupí |
| `Drone_A_Led_1..4` | LED pod motorem ramene (dítě `ArmPivot`, skládá se s ramenem), materiál `SDT_NavLed` |
| `Drone_A_LedLight_1..4` | bodové světlo pod LED (dosah 3 m, bez stínů) |
| `generatorExhaust` | výfuk elektrocentrály: kouř a zvuk |
| `colLadder` (bez mapování) | kolize žebříku pod `ladderHinge` |

Natočení kloubů složeno/rozloženo nejsou v i3d, ale v XML (`<foldPart>` pod `<sprayDrone>`, viz níž); počítá je
`blender/export_car_mod.py` z geometrie (`drone_fold_parts` v `build_trailer_car.py`: motor ramene dosedne do rohu
rozteče 1,59 × 1,90 m; horní listy se roztáhnou napříč ramene, spodní podél). Náhled v Blenderu:
`set_drone_unfold(0..1)`.

Při vzletu skript `droneRoot` přepojí pod kořen scény (`link(getRootNode(), node)` se zachovanou
světovou polohou) a řídí jeho `setWorldTranslation/Rotation`. Po přistání ho vrátí pod vlek do
původní lokální polohy. Dron nemá fyziku (kinematický let), překážky hlídají raycasty (sekce **Překážky**).

## Parametry (výchozí, v XML vozidla `vehicle.sprayDrone`)

Sekce `<sprayDrone .../>` je v `sprayDroneTrailerCar.xml` i v šabloně `blender/templates/sprayDroneTrailerCar.xml.in`
(statický text). `vehicle.xsd` ji nezná, takže `tools/validate_mod.py` na ní hlásí chybu schématu — to je v pořádku.

| parametr | hodnota | poznámka |
|---|---|---|
| `node` | `droneRoot` | kořen dronu v i3d |
| `fillUnitIndex` | 1 | nádrž vleku, ze které se dron doplňuje |
| `range` | 300 m | poloměr dosahu od vleku |
| `workWidth` | 9 m | záběr postřiku, T50 udává 4 až 11 m |
| `tankCapacity` | 40 l | nádrž dronu |
| `batteryMinutes` | 8 | výdrž baterie ve vodorovném letu s plnou nádrží (do 0.5: 9 min bez ohledu na zátěž) |
| `droneMass` | 52 kg | dron s baterií bez náplně (T50: 39,9 kg + baterie 12,1 kg) |
| `batteryHoverFactor` | 1,15 | násobek odběru při vznášení a otáčení na místě (pod 2 m/s vodorovně) |
| `batteryClimbFactor` | 1,4 | násobek odběru při stoupání (nad 0,5 m/s) |
| `batteryDescentFactor` | 0,8 | násobek odběru při klesání |
| `batterySwapBelow` | 0,3 | na vleku se baterie vymění, když je pod 30 % (nebo když na další dávku nestačí) |
| `trailerFoldEnd` | 0,667 | dron se skládá v čase 0..0,667 skládání vleku (0 = rozloženo), tj. prvních 2 s ze 3 |
| `cruiseSpeed` | 10 m/s | přelet a přejezdy mezi řádky |
| `sprayingSpeed` | 7 m/s | rychlost při postřiku |
| `climbSpeed` | 3 m/s | klesání (u země ještě zpomaluje, viz Let) |
| `ascentSpeed` | 5 m/s | stoupání |
| `acceleration` | 2,5 m/s² | rozjezd i brzdění, vodorovně i svisle |
| `yawSpeed` | 90 °/s | nejvyšší rychlost otáčení |
| `sprayHeight` | 3 m | výška nad terénem při postřiku |
| `transitHeight` | 12 m | nejnižší výška přeletu vlek ↔ pole nad terénem |
| `obstacleClearance` | 5 m | odstup přeletu nad nejvyšší překážkou úseku |
| `maxTransitHeight` | 60 m | výš dron nesmí; překážka nad limit = dávku nejde letět |
| `corridorHeight` | 8 m | nejnižší výška přeletu letovou plochou (místo `transitHeight`, když je plocha nakreslená) |
| `usageScale` | 1 | násobek spotřeby oproti vanilla (jako `usageScale` u `Sprayer`) |
| `litersPerSecond` | 1 l/s | čerpadlo, kterým se dron na plošině plní z nádrže vleku (60 l/min, 40 l za 40 s; původně 0,4 l/s, Pavel chtěl 2,5× rychleji) |
| `securedFoldTime` | 0,8 | od kterého času skládání vleku jsou úchyty lyžin zavřené („Dron zajištěn") |
| `power#dieselFillUnitIndex` | 2 | nádrž elektrocentrály (nafta, 30 l) |
| `power#spareBatteries` | 2 | náhradní baterie na vleku (vedle té v dronu), 1–8 |
| `power#chargeMinutes` | 10 | nabití jedné baterie z 30 % na 95 % (DJI D12000iE + DB1560: 9–12 min) |
| `power#dieselPerHour` | 2,2 l/h | spotřeba centrály, jen když nabíjí |
| `power#readyLevel` | 0,95 | od kolika procent jde náhradní baterie do dronu |
| `power#swapTime` | 5 s | výměna baterie (souběžně s plněním) |
| `navLights#intensity` | 4 | svit LED ramen (`lightIds0` materiálu) |
| `navLights#lightScale` | 0,3 | násobek barvy bodových světel pod LED (plná barva z i3d celý dron přesvěcovala) |
| `navLights#blinkPeriod`, `#blinkOn` | 1 s, 0,5 s | blikání zadních LED (1 Hz, střída 50 %) |

Pod `<sprayDrone>` jsou uzly dronu (generuje je export z Blenderu): `<tilt node>`, `<foldPart node foldedRot
unfoldedRot startTime endTime>` (klouby ramen 0–0,6 času rozložení, listy 0,5–1) a `<rotor node direction>`,
a ručně psané `<sounds><rotor .../></sounds>` (sekce Zvuk) a `<effects>` (sekce Efekt postřiku). Konstanty vizuálu jsou ve skriptu: roztočení 2 s,
doběh 4 s, vrtule 35 rad/s.

### Rozložení dronu s vlekem

Animace skládání vleku `foldLadder` trvá 3 s (konvence FS25: čas 0 = rozloženo, 1 = složeno): 0–2 s nic
(skládá se dron), 2–2,5 s vyklopení žebříku, 2,5–3 s zasunutí. Rozložení dronu počítá skript z
`getFoldAnimTime()`: `1 - čas / trailerFoldEnd`, takže při rozkládání vleku se dron rozloží až po vysunutí žebříku
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

- **Plánování** (`SprayDroneRoute.planBatch`) počítá kromě času i spotřebu stejným vzorcem: přelet tam s plnou nádrží,
  postřik s průměrnou náplní úseku, návrat s tím, co zbude, stoupání/otáčení/klesání se svými násobky. Rezerva 30 s.
  Za letu se návrat hlídá stejně (`getReturnEnergy`). Ve hře (pole 4): odhad 42,8 / 43,9 / 46,3 / 57,8 / 46,6 s,
  skutečnost 41,5 / 40,7 / 42,5 / 52,2 / 45,1 s (o 3–10 % opatrnější, jako odhad času).
- **Výměna baterie** na vleku při servisu (`power#swapTime`, 5 s, souběžně s plněním): jen když je pod `batterySwapBelow`
  (30 %), nebo když s ní další dávka nejde naplánovat. Do dronu jde nejnabitější náhradní baterie, vybitá jde na její
  místo do nabíječky (sekce Elektrocentrála). Náhradní musí mít aspoň `power#readyLevel` (95 %); když žádná nemá, dron
  zůstane na plošině a HUD i plánovač píšou „čeká na nabití baterie – X %" (X = nejnabitější náhradní). Když přitom
  dojde nafta, mise skončí se stavem „v centrále došla nafta". Plánovač počítá dávky od aktuální baterie se stejnými
  výměnami, ukáže nejvyšší spotřebu dávky v % a počet výměn.
- O výměně se rozhodne hned na začátku servisu (`getWantsSwap`: plán další dávky s nádrží, jaká bude po doplnění),
  takže výměna běží souběžně s plněním; když náhradní ještě není nabitá, vymění se, jakmile dosáhne 95 %.
- S vanilla dávkou (~292 l/ha) vystačí 40 l jen na ~150 m řádku, takže dávku skoro vždy omezí nádrž: dávka na poli
  vedle vleku bere ~9–11 % baterie, s přeletem 300 m ~20 %. Výměna tak přijde zhruba po každé 3.–7. dávce.

### Elektrocentrála a náhradní baterie

Oranžová skříň v kleci vpředu na palubě (`Gen_0`, vzor DJI D12000iE) je elektrocentrála s nabíječkou.

- **Nafta**: druhá nádrž vleku (`fillUnit` 2, `diesel`, 30 l jako nádrž D12000iE) s vlastním `exactFillRootNode`
  (`dieselFillRootNode`, kinematický kvádr přes centrálu, skupina `0x40000000` jako plnicí uzel nádrže). Čerpací
  stanice (`gasStation01.xml`, `loadTrigger fillTypes="DIESEL"`) i nádrž na naftu na farmě plní přes `loadTrigger`,
  který hledá právě `exactFillRootNode`; bez něj by vlek nenatankoval. Ve hře ověřeno na stanici u (-798, -250):
  pickup s vlekem v triggeru, akce Natankovat (R), 2 → 30 l, −42 €. Stav je ve vanilla ukazateli naplnění a v plánovači.
- **Nabíjení**: jedna nabíječka, nabíjí se jedna náhradní baterie najednou: ta, co už na nabíječce je, dokud není
  plná, pak nejnabitější z nenabitých (dřív se uvolní baterie k výměně). Rychlost je 65 % kapacity za `chargeMinutes`
  (30 → 95 % za 10 min, 0 → 100 % za ~15 min; bez zpomalení nad 95 %). Baterie v dronu se nenabíjí.
- **Spotřeba**: `dieselPerHour` 2,2 l/h, jen když se nabíjí (centrála bez zátěže se vypne), tj. ~0,37 l na nabití
  30 → 95 %; 30 l vystačí na ~13,6 h nabíjení (~80 nabití). Hodnota: D12000iE dává 9 kW DC, jedna baterie DB1560
  (30 Ah × 52,22 V = 1,57 kWh) nabitá z 30 na 95 % je ~1,0 kWh za 10 min, tedy ~6 kW do baterie a ~7 kW z centrály
  se ztrátami; dieselová centrála má měrnou spotřebu ~0,3 l/kWh (≈250 g/kWh) → ~2,1–2,3 l/h. (Originál D12000iE je
  benzínový, DJI udává 0,5 l/kWh při 9 kW, tj. ~4,5 l/h benzínu.)
- **Kdy běží**: kdykoli je zapnutá, je nafta a některá náhradní baterie je pod 100 %: nezávisle na misi, i u složeného
  vleku a bez nikoho ve vleku (na farmě, za jízdy). Vypnout / zapnout jde akcí `SDT_TOGGLE_GENERATOR` (`Alt+6`) z vleku
  i z tahače, ke kterému je vlek zapřažený (text akce „Dron: vypnout / zapnout elektrocentrálu"); stav
  `generatorEnabled` jde eventem `SprayDroneCommandEvent.SET_GENERATOR` na server, ukládá se a synchronizuje.
  Vypnutá centrála nenabíjí ani během mise (dron pak čeká na baterii, dokud se nezapne). Během běhu hraje vanilla zvuk motorového čerpadla (`soundTemplates` `riceFieldPump`, 3D u výfuku) a z výfuku
  jde vanilla kouř (`$data/effects/exhaust/exhaust.i3d`, shader `exhaustShader`, parametry `param` a `exhaustColor`).
- **Nabíjecí stanice pro elektromobily**: nepodporuje se. Vanilla stanice (`placeables/brandless/chargingStation`,
  `loadTrigger fillTypes="ELECTRICCHARGE"`) na Riverbend Springs předem postavená není, takže by nešlo nic ověřit.
  Šlo by to přidat třetí `fillUnit` `ELECTRICCHARGE` (bez zobrazení, kapacita sady ~3,1 kWh) s vlastním
  `exactFillRootNode`: stanice by ho naplnila a skript by z něj nabíjel přednostně před naftou.
- **Uložení a síť**: náboj náhradních baterií (`spareBattery(i)#charge`), baterie na nabíječce (`#chargingSlot`) a
  zapnutí centrály (`#generatorEnabled`) jdou do `vehicles.xml`, nafta do vanilla `fillUnit`. Po síti jdou v `writeState` (nabití, nabíječka, běh centrály,
  příznaky plnění / výměny / čekání), za nabíjení nejvýš každých 0,5 s.
- `DEBUG_POWER = true` zapisuje do logu každých 10 s nabití baterií a naftu a změny běhu centrály.

### Plnění dronu na plošině

Po přistání se dron plní čerpadlem `litersPerSecond` (1 l/s = 60 l/min; 40 l za 40 s) z nádrže vleku, souběžně s
případnou výměnou baterie. Servis trvá nejméně 5 s (`SERVICE_TIME`), jinak dokud se nádrž nenaplní (nebo vlek
nevyprázdní), baterie nevymění a případně nenabije. F1 ukazuje „Dron: plní nádrž (60 l/min)" a v ukazateli naplnění
roste „Nádrž (v dronu)" (stav jde po síti každých 0,5 s). Plánovač počítá s dobou plnění před každou dávkou
(spotřebované litry / čerpadlo), s výměnou a s čekáním na nabití (simulace nabíječky a nafty v
`SprayDroneRoute.splitIntoBatches`, stejné pravidlo výběru baterie jako server), panel ukáže „Servis na vleku X min, z
toho čekání na nabití Y min" (čekání = jen o kolik se servis kvůli nabíjení prodlouží) a „Nafta na nabíjení ~Z l,
v centrále W l" (červeně s upozorněním, když nafta nestačí). Ve hře (pole 4, náhradní baterie 66 %): plánovač 3,8 min
čekání, skutečně vyměněno po ~4,5 min od startu (40 s plnění + nabíjení na 95 %).

### Ukazatel naplnění (vpravo dole)

`getFillLevelInformation` (přepsaná funkce FillUnit) přidá za vanilla řádky nádrže vleku a nafty: „Nádrž (v dronu)"
(litry, druh přípravku dronu; u složeného vleku „Nádrž (Dron zajištěn)"), „Baterie (v dronu)" a „Vlek (63/30 % nabíjí)"
jako souhrn sady náhradních baterií. Baterie jsou `ELECTRICCHARGE` v kWh jako u vanilla elektrických strojů
(`BATTERY_KWH` = 1,567 kWh DB1560, jen pro zobrazení). Vanilla ukazatel sčítá řádky stejného druhu náplně se stejným
doplňkovým textem (proto má každý řádek vlastní doplňkový text) a ukáže nejvýš 5 řádků, proto jsou náhradní baterie
v jednom řádku s procenty po kusech. F1 ukazuje jen akce, vybrané pole, počet dávek a krátký stav dronu.

### Zajištění dronu na plošině

Dron je součást i3d vleku (uzel `droneRoot` pod vizuálem hlavní komponenty) bez vlastní fyziky ani kloubu, takže se
za jízdy ani při převrácení vleku fyzicky oddělit nemůže: pohybuje se s komponentou jako kterýkoli jiný díl modelu.
Odpojí ho jen skript při vzletu (`link(getRootNode())`) a po přistání ho vrátí (`attachDrone`); vzlétnout jde jen z
rozloženého vleku, složit vlek jde jen s dronem v doku. Ve hře ověřena jízda se složeným vlekem ~36 m rovně pomalu
(dron na plošině); rychlá jízda, zatáčky a převrácení ověřené nejsou (plyne to z toho, že dron nemá fyziku).

Vizuální zajištění: 4 úchyty lyžin (`DroneClamp_i`: černý sloupek vedle lyžiny a žlutá čelist na závěsu
`droneClampHinge_i`, po dvou na každé lyžině mezi příčkou a nohami). Jsou součástí animace `foldLadder`: 2–2,4 s (po
složení dronu, souběžně s vyklopením žebříku) se čelist překlopí o 100° přes trubku lyžiny, při rozkládání se v tomtéž
úseku otevře, než se dron začne rozkládat. Stav „Dron zajištěn" (čas skládání ≥ `securedFoldTime`) ukazuje ukazatel
naplnění u nádrže dronu (viditelný z tahače; do složeného vleku nastoupit nejde). Čelisti jsou jen vizuál, nemají
kolizi ani fyziku.

### Čáry ve světě

`SDT_TOGGLE_LINES` (`Alt+5`, ve vleku) skryje a znovu zobrazí všechny čáry, které mod kreslí ve světě: kruh dosahu,
obrys vybraného pole, trasu po dávkách, přelety a letovou plochu. Výchozí stav je zapnuto, stav je jen lokální
(`SprayDroneStation.showWorldLines`, neposílá se ani neukládá, po restartu hry je zase zapnuto). Plánovač se nemění.

### Zvuk

`sounds/droneRotorLoop.ogg`: smyčka rotorů (mono, 44,1 kHz, 8,9 s, bezešvá), vzorek `vehicle.sprayDrone.sounds.rotor`
(schéma `SoundManager.registerSampleXMLPaths`), načtený `g_soundManager:loadSampleFromXML` jen u klienta, 3D
připojený k `Drone_A_Tilt` (letí s dronem), `innerRadius` 8 m, `outerRadius` 120 m, venku hlasitost 1,2, uvnitř 0,6
s dolní propustí. Hraje, dokud se vrtule točí; výška `0,45 + 0,55 × otáčky` a hlasitost `otáčky^0,7` (otáčky 0..1)
jdou přes `setSamplePitchOffset` a `setSampleVolumeScale` (přímé `setSamplePitch/Volume` by `SoundManager:update`
přepsal). Roztočení (2 s) i doběh (4 s) je tak slyšet. Otáčky plynou ze stavu letu, takže klient zní stejně.
`DEBUG_SOUND = true` vypisuje otáčky, výšku a hlasitost do logu.

Zdroj: „Big Slow Heavy Drone Hovering Idle Loop“, qubodup, https://freesound.org/people/qubodup/sounds/854382/,
**CC0 1.0** (odvozeno z CC0 nahrávky DJI Mavic Mini 2 od Sadiquecat, https://freesound.org/people/Sadiquecat/sounds/683298/).
Stažen HQ náhled bez přihlášení, výška snížena na 3/4, smyčka uzavřena crossfadem 0,6 s (`out/tmp/zvuk/make_loop.py`).
Licence a úpravy jsou v `mod/FS25_SprayDroneTrailer/sounds/LICENSE.txt`.

### Světla dronu

Pod motorem každého ramene je LED (`Drone_A_Led_i`, 7 × 7 × 2,5 cm): přední ramena (1, 2) **červená**, zadní (3, 4)
**zelená**, jako orientační světla DJI Agras (vpředu červená = nos, vzadu zelená). Přední svítí trvale, zadní blikají
1 Hz (0,5 s svítí, 0,5 s ne), dokud je dron zapnutý: letí nebo se točí vrtule (tedy i roztáčení na plošině a doběh
po přistání). Složený a stojící dron má LED zhasnuté. Stav plyne ze stavu letu a otáček vrtulí, takže je stejný
u serveru i klientů (fáze blikání z `g_time`, mezi hráči se může lišit).

- **Svit**: materiál `SDT_NavLed` je vanilla `vehicleShader` s variantou `staticLight_vertex`: barva svitu je v barvě
  vrcholů sítě (export z Blenderu, atribut `Col`), intenzitu dává parametr `lightIds0.x`, který skript nastavuje
  `setShaderParameter` (0 = zhasnuto, `navLights#intensity` = svítí). `export_car_mod.py` materiál přepisuje sám
  (`EMISSIVE_MATERIALS`).
- **Světlo**: pod každou LED je bodové světlo (Blender Point → i3d `Light`, dosah 3 m, bez stínů; exportér má
  zapnuté `i3D_exportLights`), skript ho zapíná `setVisibility` s LED.
- Malé zelené a červené destičky vpředu na lyžinách (`Drone_A_NavLight_L/R` z `build_drone.py`) zůstávají jen jako
  dekorace, nesvítí.

### Kolize žebříku

`colLadder` je kvádr podél šikmého žebříku (šířka žebříku + 4 cm na každé straně, tloušťka 10 cm), dítě `ladderHinge`,
takže se s animací `foldLadder` vyklápí i zasouvá. Je to `compoundChild` hlavní komponenty se stejnou skupinou a maskou
jako ostatní kolize vleku (`0x10004` / `0xfe3ffb83`, vzor ABI Water Trailer), `density` 0,001; kolize uvnitř jedné
komponenty spolu nekolidují, takže zasunutý žebřík pod plošinou nepřekáží vleku. Končí 25 cm nad zemí
(`LADDER_COL_MIN_Z`): kdyby se dotýkal terénu, zvedal by vlek. Hráč tak žebříkem neprojde, pod spodní příčlí se ale
dá strčit noha (do 25 cm).

### Efekt postřiku

`vehicle.sprayDrone.effects` (schéma `EffectManager.registerEffectXMLPaths`): 4× vanilla síť postřiku `backArmEffect`
z `$data/vehicles/hardi/mega1200L/mega1200L.i3d` (`filename` + `node="0|0|1|0|0|0|8"`, načte ji `g_effectManager:loadEffect`
ze sdíleného i3d, nic se do modu nekopíruje), `linkNode="Drone_A_Tilt"` (naklání se s dronem), `materialType="sprayer"`:
materiál podle přípravku (`setEffectTypeInfo`, hnojivo / herbicid) z `$data/effects/sprayer/sprayerMeshes_materialHolder.i3d`.
Síť je 5,84 × 2,04 m, viditelný postřik je ale jen ~1,5 m uprostřed (`meshWidth="1.5"`). Skript (`placeSprayEffects`,
až při prvním startu, protože síť se načítá asynchronně) je postaví napříč dronem vedle sebe na `workWidth` (4 × 2,25 m),
natočené podle kořene dronu (`Drone_A_Tilt` má jiné osy), a na výšku od trysek (`nozzleY` −0,2 m pod `Drone_A_Tilt`) k zemi
ve výšce postřiku + 0,5 m; spodek pod terénem shader ořízne (`isFadeAboveTerrain`).

Běží, jen když dron opravdu stříká (waypoint `spray`, náplň > 0, drženo 150 ms jako `Sprayer:getAreEffectsVisible`);
roztočení a doběh je vanilla fade 1 s. Stav `sprayEffectsActive` i druh náplně dronu jdou v `writeState`, takže klienti
efekt pouštějí sami (`updateSprayEffects`).

Spotřeba: vanilla `Sprayer:getSprayerUsage` = `litersPerSecond × rychlost[km/h] × záběr` za sekundu, tedy na metr
dráhy `litersPerSecond × 3,6 × záběr` (tekuté hnojivo i herbicid 0,0081 l/s → ~292 l/ha, 0,26 l/m při 9 m).
Jedna nádrž 40 l tak vystačí na ~150 m řádku (~0,14 ha).

## Ovládání

Klávesy platí jen ve vleku (stanoviště pilota), texty jsou v nápovědě F1:

| akce | klávesa | kdy jde |
|---|---|---|
| Dron: plánovač letu (`SDT_OPEN_PLANNER`) | `Alt+7` | kdykoli ve vleku |
| Dron: spustit let (`SDT_START_FLIGHT`) | `Alt+8` | pole je vybrané, mise neběží (rychlá akce bez plánovače) |
| Dron: návrat na vlek (`SDT_RETURN_HOME`) | `Alt+0` | mise běží nebo dron letí (rychlá akce bez plánovače) |
| Dron: zapnout/vypnout elektrocentrálu (`SDT_TOGGLE_GENERATOR`) | `Alt+6` | ve vleku i v tahači s vlekem |
| Dron: zobrazit/skrýt čáry ve světě (`SDT_TOGGLE_LINES`) | `Alt+5` | ve vleku |

`Alt+5` a `Alt+6` ve hře s ničím nekolidovaly (ve vleku i v pickupu: jen text akce se přepne, vanilla na `5` / `6`
v těchto vozidlech nic nemá); v nastavení ovládání se konflikt nekontroloval.

### Plánovač letu

Celoobrazovková herní mapa (stejná jako v menu mapy, s ikonami vozidel a čísly polí), při otevření přiblížená
tak, aby se na výšku vešlo zhruba 2,8× dosah, a vycentrovaná na vlek vlevo od panelu. Posun tažením myši,
zoom kolečkem.

- **Vlek**: oranžový čtvereček s popisem VLEK (vedle vanilla ikony vozidla). **Dron** ve vzduchu: azurový
  čtvereček.
- **Kruh dosahu**: azurová kružnice o poloměru `range`.
- **Pole** do dvojnásobku dosahu mají obrys: zelená = vybrané, modrá = vlastní a v dosahu, zlatá = zakázka, na
  které dron smí postřikovat, červená = nejde (cizí pole, mimo dosah, zakázka na jiný přípravek nebo práci).
  Pole se zakázkou farmy mají navíc zlatý popisek „zakázka". Pole pod kurzorem se obtáhne bíle a panel napíše,
  jestli jde vybrat, případně proč ne.
- **Klik na pole** ho vybere (příkaz jde přes event na server, jako dřív `Alt+7`). Když vybrat nejde, důvod se
  ukáže v panelu. Za letu pole změnit nejde.
- **Trasa**: řádky vybraného pole, barva čáry = číslo dávky. Za letu se každých 5 s přepočítá, takže hotové
  řádky mizí.
- **Panel vpravo**: obsah vleku a přípravek, stav dronu (nádrž, baterie), dosah a záběr; u vybraného pole typ
  (vlastní / zakázka s postupem v %), letová plocha (počet bodů, fialově), počet dávek, odhad času letu v minutách,
  délka přeletu (tam a zpět u 1. dávky, celkem za všechny dávky; „přímo" nebo „plochou"), výška přeletu (žlutě, když
  je zvednutá kvůli překážkám; červené varování nad limitem 60 m), plocha k ošetření, potřebné litry proti obsahu
  vleku a dronu (červeně, když nestačí), přípravek, upozornění, že část pole je mimo dosah, a stavová hláška mise.
- **Přelety**: bílé čárkované čáry z vleku k začátku každé dávky a z konce zpět, po skutečné cestě (s letovou plochou
  lomené).
- **Tlačítka** dole: `Enter` Spustit let (jen když je vybrané pole a je co dělat), `Mezerník` Návrat domů (jen
  když mise běží nebo dron letí), `X` Kreslit / Upravit letovou plochu, `Backspace` Smazat plochu (jen když
  nějaká je), `Esc` Zavřít. Plánovač se sám zavře, když hráč z vleku vystoupí nebo se vlek složí.

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

### Chování

- **Kruh dosahu ve světě**: azurový „plot" (čáry ve výšce 0,5 m a 4 m se sloupky) kolem vleku, vybrané pole
  obtažené zeleně a trasa jako debug čáry. Debug čáry mají hloubkový test, takže za stromy a za kopcem vidět
  nejsou.
- **Trasa**: řádky rovnoběžné s nejdelší hranou pole, rozteč `workWidth`, začíná se od strany bližší vleku, směr
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
- **Odhady**: plánování dávek (baterie) i souhrn v plánovači počítají s rozjezdem a brzděním na každém waypointu,
  otáčením, stoupáním `ascentSpeed` a pomalým dosednutím. Změřeno ve hře (pole 2): odhad letu dávky 100 / 110 /
  129 s proti skutečnosti 97 / 108 / 122 s, tedy o 2–6 % opatrnější. Souhrn přičítá roztočení a servis.
- **Návrat**: dron zabrzdí po směru letu, vystoupá do výšky přeletu úseku k vleku, vrátí se a přistane; mise se
  zastaví. Další start pokračuje jen po neošetřených místech (trasa se vždy počítá ze stavu pole). Start během
  návratu misi obnoví: dron dosedne, doplní se a letí dál. Návrat ještě na plošině (během roztáčení) nevzlétne.

### Překážky

- **Plánování**: každý přeletový úsek (vlek → začátek dávky, konec dávky → vlek, návrat) se projede po 5 m svislými
  paprsky shora (`raycastClosest` od terénu + 120 m dolů) v pásu 0, ±1,2 a ±2,4 m kolem osy. Maska
  `STATIC_OBJECT + TREE + BUILDING` (0x1802): terén ani vozidla (vlastní vlek, tahač) do ní nepatří, dron kolize nemá.
  Výška přeletu úseku = max(nejvyšší překážka + `obstacleClearance`, `transitHeight`; s letovou plochou
  `corridorHeight`), cesta plochou má výšku pro každý svůj úsek. Pak se ve zvolené výšce
  pás proletí vodorovnými paprsky; co svislé paprsky minuly (kmen a větve stromů mezi vzorky), výšku zvedne
  po 2 m. Výsledky se pamatují podle úseku a nejnižší výšky. Plánovač ukáže nejvyšší výšku přeletu všech dávek,
  žlutě „kvůli překážkám v cestě", když je nad `transitHeight` (s plochou nad `corridorHeight`).
- **Limit**: překážka, kvůli které by přelet musel nad `maxTransitHeight` (60 m), dávku zablokuje: plánovač napíše
  „Překážka v cestě převyšuje limit 60 m – přeparkuj vlek", Spustit let nejde (u první dávky) a mise se u takové
  dávky ukončí se stavem „v cestě je překážka".
- **Pojistka za letu**: při vodorovném pohybu (ne při přistání) letí každý snímek tři paprsky dopředu (osa a ±1,2 m)
  na brzdnou dráhu + 4 m. Při zásahu dron zabrzdí, stoupá, dokud paprsek neprojde, a ještě 2 m; pak letí dál
  o tolik výš a klesá zpět, až pod ním nic není. Na poli (postřik ve 3 m) se překážky řeší jen touto pojistkou.
  Ve hře na poli 2 zasáhla u stromů na dvoře farmy, které plánování nezachytilo (1× za 2 dávky po zhuštění pásu,
  předtím 5×), a vystoupala o 2,6–10 m.
- **Složení vleku** (X z auta) za letu: nesloží se, zobrazí se varování a dron se vrací. Rozjetí vleku
  rychleji než 3 km/h za letu vyvolá totéž. Složení během doplňování misi ukončí.
- Vystoupení z vleku let nepřeruší.

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
  `droneFillLevel`, `droneFillType`, `battery` a pod tím `flightArea(i)#fieldId` s `point(j)#x/#z`. Když byla
  mise aktivní, dron po načtení stojí na vleku a za 3 s sám pokračuje zbytkem pole.

## Testování ve hře

- `tools/prepare_testsave.py` připraví slot 11: pickup s vlekem u pole 4 (600l nádrž, 300 l tekutého hnojiva,
  s `--herbicide` herbicidu) a dvě běžící zakázky farmy 1: hnojení na poli 9 (bavlna, sprayLevel 0 → 1, v dosahu
  je jen roh pole) a herbicid na poli 8 (kukuřice, plevel 3 → 7). Vlastní pole v dosahu: 2, 3, 4, 5. Centrála má
  20 l nafty, baterie jsou plné. Volby: `--diesel L`, `--batteries 25,40,30` (dron a náhradní v %), `--time 22:00`
  (denní doba, výchozí 08:28 jako v kopii slotu), `--unfolded` (rozložený vlek), `--player-at-ladder` (hráč pěšky
  2 m za žebříkem, čelem k němu – test kolize), `--at=x,y,z,yaw` (souprava jinde, např.
  `--at=-802.07,59.3,-252.70,-114` u čerpací stanice na severozápadě farmy). Bez voleb vrací hráče na výchozí spawn.
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
- Uložení ve hře: Esc → poslední ikona (Nastavení) → Uložit hru; pak `savegameBackup/savegame11_backup<čas>` drží
  stav před uložením, z něj jde slot 11 vrátit a znovu pustit `prepare_testsave.py`.
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
- Stromy mají kolizi jen na kmeni a větvích (listí ne), takže odstup `obstacleClearance` se počítá od dřeva;
  koruna může do přeletu zasahovat. Úsek se vzorkuje jen v pásu ±2,4 m a po 5 m, řídké větve občas proklouznou
  a řeší je až pojistka za letu (zastavení a stoupání).
- Pojistka za letu hlídá jen vodorovný pohyb; svislé stoupání a klesání (vzlet, sestup na pole, přistání) ne.
  Kolizi se statickým objektem kolmo pod dronem při sestupu na pole to neřeší.
- Odhad času dávky je o 2–6 % delší než skutečnost (počítá se zastavením i tam, kde dron v řádku jen pokračuje
  přes mezeru), baterie proto vychází s rezervou.
- Zbytek přípravku v dronu se při jiném typu ve vleku zahodí (nevrací se do vleku).
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
- Efekt postřiku je vanilla „závěs“ z trysek ramene postřikovače, ne mlha z odstředivých trysek dronu, a ke svislé
  ose se nenaklání podle směru letu (jen s náklonem dronu). Závisí na vnitřní cestě uzlu v `mega1200L.i3d`; když ji
  GIANTS v patchi změní, efekt se nenačte (hra zapíše varování, jinak nic nespadne).
- Baterie: odběr při vznášení se pozná jen podle vodorovné rychlosti pod 2 m/s, vítr ani náklon se nepočítají.
  Nabíjení je lineární až do 100 % (skutečná nabíječka nad 95 % zpomaluje), baterie v dronu se na plošině nenabíjí,
  opotřebení baterií (cykly) se nepočítá. Nabíjení i let jdou v reálném čase vozidla: zrychlení času hry je nezrychlí.
- Nabíjení z vanilla nabíjecí stanice pro elektromobily není (sekce Elektrocentrála).
- Ukazatel naplnění zkracuje dlouhé texty (asi nad 20 znaků názvu a doplňku), proto jsou popisky krátké; při 3 a víc
  náhradních bateriích se procenta po kusech už nevejdou celá.
- Úchyty dronu jsou jen vizuál; dron drží na vleku to, že je součástí modelu. Převrácení vleku ve hře nezkoušeno.
- Bodové světlo LED je dost silné, na blízku dron nasvítí do červena/zelena (`navLights#lightScale`).
- Odhad plánovače simuluje nabíječku po 5s krocích a předpokládá, že vlek zůstane rozložený a mise nepřerušená.

## Stav

- [x] Vlek: nádrž 600 l na `liquidFertilizer` a `herbicide`, skládací žebřík, nastoupení jen rozloženého
      (`scripts/SprayDroneStation.lua`), dron jako součást modelu (`droneRoot`)
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
- [ ] Zakázka dokončená dronem celá (nevyzkoušeno, trvá desítky minut; výpočet postupu je vanilla)
- [ ] Multiplayer ve hře (kód napsaný, neověřený)

## Na příště (Pavlovy poznámky po 0.7.0.0, 2026-09-28)

1. Dron se skládá plynule, ale rozloží se najednou — rozkládání má být stejně plynulé jako skládání.
2. Ukazatele vpravo dole seskupit: dole vlek (nádrž vleku, baterie ve vleku, nafta), nahoře dron (nádrž, baterie).
   Teď jsou promíchané.
3. Po odpojení vlek spadne dolů — nefunguje opěrné kolečko (podpěra při odpojení).
4. Baterie přepracovat: vlek nemá vlastní baterii, jen **sloty** na baterie stejného typu jako v dronu (0–4 kusy,
   volitelné). Po přistání si dron vezme první plně nabitou baterii a svou vybitou vloží do vleku k nabíjení.
   Když nejsou všechny nabité a vlek je v provozu, běží elektrocentrála, bere naftu a nabíjí.
5. Úchyty (kotvy) dronu mají při odklopení/rozložení prostě zmizet, ne se jen otevřít.
6. (Můj nález) Bodové světlo LED nasvítí na plošině celý vlek do červena — zeslabit nebo vypnout bodová světla,
   když dron stojí na vleku.
7. Efekt postřiku se při záběru 9 m roztáhne moc do šířky a vypadá divně — upravit (tvar/šířka efektu). Záběr 9 m
   zůstává.
8. Zatáčky trasy mírně zaoblit, ne lomit v pravém úhlu.
9. V nastavení měnit výšku přeletu nad objekty a boční odstup od objektů.
10. Vyhýbání překážkám: dron se stromu vyhne jen tak, aby nekolidoval jeho střed/trup, ale obrys (vrtule, efekt)
    stromem stejně proletí. Počítat s odstupem od objektu a obchozí trasu i překážky ukázat v mapě plánovače.
11. Na horní plošinu pod dron namalovat heliportové „H“ v kruhu.
12. Stoupání a klesání za letu po plynulé křivce (jako zaoblené zatáčky), ne schodovitě.
13. Dosah (kruh dosahu) počítat z energie baterie místo pevného poloměru: dron musí zvládnout doletět s plnou
    nádrží k nejvzdálenějšímu bodu trasy a vrátit se prázdný zpět s rezervou. Baterie je velká, takže dosah vyjde
    větší než dnes. Závisí na výšce přeletu (stoupání stojí energii), takže kruh/perimetr se mění s nastavenou výškou.
    (Ověřit s Pavlem, jestli „vrátit plný“ znamená s plnou nádrží, nebo s rezervou v baterii.)
14. Vyprazdňování, aby šlo přejít z hnojiva na herbicid: dron vypustit zpět do nádrže vleku; nádrž vleku vypustit do
    IBC palety, která je ve hře (vanilla výměna náplně přes přečerpání).
15. Baterie jako model: domodelovat baterii a udělat pro ni místa na vleku. Při přepravě stojí baterie v držáku vedle
    centrály; po rozložení se přesunou do rohu horní paluby (aby bylo vidět, že se mění). Navazuje na bod 4: slotů na
    vleku je o jeden víc než baterií v provozu, aby při přepravě v dronu žádná baterie nezůstala (všechny jsou ve
    vleku). Dron si ji po rozložení vezme a po přistání vymění.
16. Plnicí hadice: při rozložení vleku se na horní palubu vysune hadice s koncovkou, která se při plnění připojí
    k dronu (a odpojí před vzletem).
