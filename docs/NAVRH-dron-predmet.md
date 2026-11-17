# Návrh: dron a baterie jako samostatné předměty (2026-10-22; etapa 0 hotová, viz kap. 9; etapa 1 napsaná, viz kap. 12; skenovací dron jako samostatný typ viz kap. 10)

Cíl podle Pavla: vlek se kupuje bez dronu, dron (S / M / L, později skenovací a jiné typy) se kupuje zvlášť a k vleku se
„přiřadí“ tím, že ho hráč položí na plošinu. Baterie jsou kupované kusy, které jde nosit a měnit. Na farmě může být víc
vleků i dronů a hráč je mezi sebou přehazuje.

## 1. Současný stav (dron = konfigurace vleku)

- **Volba dronu je konfigurace obchodu** `sprayDrone` (`SprayDroneStation.DRONE_CONFIG`, `scripts/SprayDroneStation.lua:119`,
  schéma `:480`). Middle: S 7 000 / M 12 000 / L 22 000 € (`vehicles/sprayDroneTrailerMiddle/sprayDroneTrailerMiddle.xml:434-448`),
  Max dvojnásobek za dva drony (`sprayDroneTrailerMax.xml:528-552`). Vlek sám: Mini 3 900, Middle 6 100, Max 48 000 €.
- **Všechny varianty dronu jsou v i3d vleku**, konfigurace jen vybere jednu a ostatní skryje: `<drone name prefix>` bloky
  (`sprayDroneTrailerMiddle.xml:583/632/703`), výběr a skrytí `SprayDroneStation.lua:560-620`. Parametry varianty (nádrž,
  záběr, hmotnost, baterie, dosah) čte `value()` z bloku varianty, `SprayDroneStation.lua:955-1000`
  (`VARIANT_FLOATS` `:131`).
- **Druhý dron (Max)**: blok `drone#slot="2"`, `spec.numDrones = 2` jen když existuje `secondVariant` (`:968`). Dron 2 je
  pohled `SprayDroneDrones.createView` (`scripts/SprayDroneDrones.lua:18`), přepínání `runAs` / `forEach` (`:67`, `:84`).
  Pole se dělí na sdílená a per-dron v `scripts/SprayDroneFields.lua:8` (shared) a `:37` (drone); hlídá to
  `tools/audit_spec_fields.py`.
- **Baterie jsou konfigurace** `sprayDroneBattery` (počet 0–6 Middle, 0–10 Max, 1 500 €/ks; `:109`, `:428`,
  `sprayDroneTrailerMiddle.xml:457-463`). Za běhu je to pool `spec.batteries` s `level` a `slot` (0 = v dronu, 1..N = šachta
  nabíječky), u dvou dronů navíc `battery.drone` (`SprayDroneStation.lua:1065-1112`). Výměna je automatická animace
  (`SprayDroneService.lua:375` `startBatteryMove`, `:284` `updateBatteryVisuals`), nabíjí centrála. Hmotnost baterie je
  parametr varianty (S 6,6 / M 12,1 / L 14,7 kg) a přičítá se k dronu (`SprayDroneStation.lua:984-986`).
- **Savegame**: dron 1 přímo pod klíčem vleku, dron 2 v `.drone2` (`:501-503`, načtení `:1094`, uložení `:1228-1301`),
  baterie `.battery(?)#level/#slot/#drone` (`:504-509`, `:1272-1276`).
- **MP**: `writeState` posílá blok dronu 1 a pro `numDrones > 1` přilepí `writeDroneBlock` dronu 2 (`:5436`, `:5521`),
  baterie se slotem v `batterySlotBits` bitech (`:5503`, `:5552`); join `onWriteStream`/`onReadStream` (`:5600`, `:5615`).
- **Anténa a RTK** jsou konfigurace vleku (`rangeBonus` násobí dosah, `usageFactor` a nově `spotMargin` u RTK;
  `sprayDroneTrailerMiddle.xml:467-479`, `SprayDroneStation.lua:96`).
- **Vzor „předmět ↔ slot na vleku“ už existuje dvakrát**: relé tyče (`scripts/SprayDroneRelaySlots.lua`, load/save
  `:167/:205`, MP `:247/:257`, hledání drženého/ležícího předmětu `:355/:369`) a přenosná pumpa
  (`scripts/SprayDronePumpSlots.lua`, `:77/:109/:162/:173/:199/:214`). Obojí: předmět se při uložení smaže, slot si pamatuje
  jeho stav, při vyndání se znovu vyrobí přes VehicleLoadingData.

Důsledek: dron dnes není objekt, je to sada uzlů vleku plus pole ve `spec`. Let, trasy, hadice, kamera, sken i baterie
počítají s tím, že dron patří právě jednomu vleku a jeho varianta se po načtení nemění.

## 2. Cílový model

### Entity

| Entita | Co nese | Kde žije |
|---|---|---|
| **Vlek** | nádrže, centrála, mixér, nabíječka (N šachet), **plošiny 1..P** (Mini/Middle 1, Max 2), anténa | vozidlo jako dnes |
| **Dron (předmět)** | typ (`spray` / `scan` / později `seed`), varianta (S/M/L), RTK ano/ne, náplň (l + druh), vložená baterie (nabití) | v ruce / na zemi / na korbě = objekt; na plošině = stav plošiny vleku |
| **Baterie (předmět)** | velikost (S/M/L), nabití 0..1 | v ruce / na zemi = objekt; v šachtě nebo v dronu = stav vleku |

Opotřebení dronu zatím ne – bez navázané mechaniky (servis, porucha) by to bylo jen číslo „na oko“.

### Kde žije stav letu

Let musí zůstat **ve vleku**. Dron na plošině se pro kód chová přesně jako dnešní konfigurovaný dron: vlek zapne svou
variantu v i3d a nastaví parametry z bloku varianty. Celá letová logika (`SprayDroneDrones`, trasy, sken, hadice, MP stav)
zůstává beze změny; mění se jen **to, kdy a odkud se varianta vybírá** – místo jednou při načtení z konfigurace
kdykoli za běhu podle toho, co na plošině leží. Dron mimo vlek je hloupý objekt bez logiky.

### Varianta A – dron jako předmět, plošina jako slot (vzor RelaySlots/PumpSlots) — doporučeno

- Hráč přinese dronový předmět k plošině a R ho „usadí“: předmět se smaže, plošina si zapíše typ/variantu/RTK/náplň/baterii
  a vlek přepne variantu (`applyDroneVariant(self, droneIndex, variant)` – vyčleněná část dnešního `SprayDroneStation.lua:560-620`
  a `:955-1000`). R na prázdnou ruku u plošiny dron sundá: vlek variantu skryje a vyrobí předmět se stejným stavem.
- Sundat jde jen dron, který stojí doma, je složený a neběží mu servis (stejná podmínka jako dnes u výměny baterie / hadice).
- Výhody: letová logika se nedotkne, vzor je ozkoušený dvakrát, MP i savegame jsou jen „stav plošiny“.
- Rizika: varianta se dnes čte jen v `onLoad` – po přepnutí za běhu se musí přepočítat vše, co z ní vzniklo (kolize,
  kamery `attachDroneCamera`, hadice dronu, `fullMass`, dosah, cache trasy, `pfDose`, náhled plánovače). To je hlavní práce
  a hlavní zdroj chyb. Model předmětu potřebuje vlastní i3d (stačí jedno i3d na velikost se složenými rameny, export
  z existujících `blender/build_drone.py` dílů).

### Varianta B – dron jako samostatné vozidlo

- Dron by byl vlastní vozidlo se specializací letu; vlek jen nabíječka a nádrž.
- Výhody: čistý model, dron může létat i bez vleku, libovolné párování.
- Rizika: přepis celé letové logiky (dnes ~6 000 řádků Station plus Route/Service/Drones svázaných se `spec` vleku), nové
  MP synchronizace za letu, hadice a servis přes dvě vozidla, fyzika vozidla ve vzduchu. Odhadem několikanásobek A a
  dlouho rozbitý mód. **Nedoporučuji.**

## 3. Baterie

- **Předmět**: kus na velikost S / M / L (6,6 / 12,1 / 14,7 kg – v limitu ruky ≈ 200 kg s velkou rezervou), objekt podle vzoru
  kanystru (`objects/canister`), nese nabití. Kupuje se v obchodě (1 500 € / M, S levnější, L dražší).
- **Šachty nabíječky** zůstávají: R s baterií v ruce u nabíječky ji zasune do volné šachty (smaže objekt, zapíše `level`),
  R prázdnou rukou vyndá nejnabitější. Dnešní pool `spec.batteries` se nemění, jen se plní z předmětů místo z konfigurace.
- **Výměna v dronu** zůstává automatická (dnešní animace) – ruční výměna by jen přidala klikání. Baterie musí pasovat
  velikostí na dron; nepasující v šachtě se nabíjí, ale do dronu ji servis nevezme.
- Dron sundaný z plošiny si nese baterii, která v něm je; ostatní baterie zůstávají ve vleku.

## 4. Obchod a ceny

- Vlek se prodává **bez dronu a bez baterií** (konfigurace `sprayDrone` a `sprayDroneBattery` zmizí). Ceny vleku zůstanou,
  dron a baterie se platí zvlášť.
- Drony (předměty, kategorie BZUK vybavení): postřikový S 7 000, M 12 000, L 22 000 € (dnešní ceny za kus);
  skenovací (jedna velikost, bez nádrže) např. 6 000 €. RTK jako konfigurace dronového předmětu (+2 500 €).
- Baterie: S 1 000, M 1 500, L 2 200 €.
- **Anténa** zůstává na vleku (patří k vysílačce). **RTK** se přesouvá na dron (přesnost je vlastnost letadla) – dnešní
  `usageFactor` a `spotMargin` se pak čtou z plošiny, ne z konfigurace vleku.
- Volitelně „sada“ v obchodě: vlek + dron M + 3 baterie za součet cen, aby nový hráč nekupoval tři položky.

## 5. Savegame a multiplayer

- **Savegame** (zpětnou kompatibilitu Pavel neřeší): plošina `.pad(?)#type/#variant/#rtk/#fillLevel/#fillType/#battery`,
  baterie jako dnes. Rozumný výchozí stav pro starou hru: pokud vlek má starou konfiguraci dronu, při prvním načtení ji
  převést na obsazenou plošinu a baterie z konfigurace na baterie v šachtách – pár řádků, ušetří Pavlovi testovací sloty.
- **MP**: stav plošiny (typ, varianta, RTK) se přidá do `writeState` před bloky dronů a změna plošiny jde eventem (vzor
  `SprayDronePumpSlotEvent`). Klient po změně volá stejné `applyDroneVariant` jako server. Za letu se nic nového neposílá.
- Pozor na `numDrones`: dnes je fixní po načtení. Max s jedním obsazeným padem musí běžet jako jednodronový (`activeDrones`
  už existuje, `numDrones` může zůstat 2 a prázdná plošina = dron „neexistuje“ pro plán).

## 6. Rizika, prototyp a etapy

**Nejdřív ověřit ve hře (prototyp, bez nového modelu):** přepnutí varianty dronu za běhu ladicím příkazem
(`droneVariant S|M|L|none`) na rozloženém Middle: model, kolize, kamera, hadice, plán, let, sken, uložení a načtení.
Pokud tohle projde, zbytek je převážně ozkoušený vzor slotů. Pokud ne, víme to dřív, než vznikne model a obchod.

| Etapa | Obsah | Ověření ve hře |
|---|---|---|
| 0 | `applyDroneVariant` za běhu + ladicí příkaz, prázdná plošina = vlek bez dronu | přepínání S/M/L/žádný na Middle a Max, let, sken, savegame |
| 1 | Dronový předmět (i3d složeného dronu S/M/L, XML, obchod), usazení / sundání R na plošině, event, savegame | koupit, nést, usadit, letět, sundat, přenést na druhý vlek |
| 2 | Baterie jako předmět, zasunutí / vyndání z nabíječky, velikost musí pasovat | koupit, nabít, vyměnit, přenést mezi vleky |
| 3 | Konec konfigurací dronu a baterií, převod staré hry, RTK na dronu, ceny | nový nákup v obchodě, stará hra se načte s dronem na plošině |
| 4 | ~~Skenovací dron jako vlastní typ~~ → přesunuto do etapy 0b, viz kap. 10 | |

Nejlevnější první krok je etapa 0: je to čistě Lua, bez modelů a obchodu, a odpoví na jedinou otázku, na které celý návrh
stojí – jestli jde variantu dronu měnit za běhu.

Další rizika: Mini má skládací bednu s dronem (`SprayDronePad`) – plošina tam je uvnitř bedny, usazení musí jít jen při
otevřené bedně. Hmotnost dronu L s baterií (75 kg) je pod limitem ruky, ale nesení velkého dronu v ruce může vypadat
divně – alternativa je nosit ho jen jako paletu/předmět na korbě (vanilla `dynamicMount`).

## 7. Otevřené otázky pro Pavla

1. **Varianta A (předmět + plošina, letová logika zůstává ve vleku)?** Doporučuji ano, B je přepis celého módu.
2. **Kam patří RTK – dron, nebo vlek?** Doporučuji dron (přesnost je vlastnost letadla, a s víc drony to dává volbu).
3. **Má dron opotřebení / servis?** Doporučuji zatím ne, dokud k tomu není mechanika, která by ho dávala smysl.
4. **Výměna baterie v dronu ručně, nebo dál automaticky?** Doporučuji automaticky; ručně jen vkládání a vyndávání z nabíječky.
5. **Nést dron v ruce, nebo jen převážet (korba, paleta)?** Doporučuji v ruce pro S a M, L jen na korbě – a rozhodnout až po
   etapě 0.

## 8. Rozhodnutí Pavla (2026-10-22)

- Varianta **A** (dron jako předmět, plošina jako slot).
- **RTK na dronu**, anténa zůstává na vleku.
- Baterie: ručně jen vkládání do nabíječky a vyndávání z ní, výměna v dronu automaticky.
- **Všechny drony (S, M, L) jdou nést v ruce, ale jen složené** (ramena a listy ve složené poloze; předmět dronu je
  vždy složený model, rozložený je jen na plošině vleku).
- Opotřebení: neotázáno, platí doporučení (zatím ne).

## 9. Výsledek etapy 0 (2026-10-22): varianta dronu jde měnit za hry

**Funguje.** `SprayDroneStation.setPadDrone(self, padIndex, name)` (`scripts/SprayDronePadDrone.lua`, zatím volané jen ladicími příkazy
`pad1None/S/M/L`, `pad2None/S/M/L`) přepne dron na plošině tak, jako by byl vlek koupený s tou konfigurací: model a úchyty, parametry letu (nádrž,
záběr, hmotnost, výdrž a typ baterie, dosah, čerpadlo, práh větru), nabíjení, vrtule, zvuky a mlha, hadice, kamera, počet dronů. Ve hře na Maxu
proletěl sken s jedním dronem S a sken i postřik podle skenu se dvěma L po výměně, Middle prošel M → S → žádný → M, varianta přežije uložení
a restart. Podrobnosti a snímky: `docs/DRON.md`, sekce „Dron na plošině za hry“.

Úpravy kvůli tomu: z `loadParameters` se vyčlenilo `loadVariantParameters`, z `loadPower` `loadChargeParameters`, z `loadDroneVariant` výběr uzlů
`selectPadVariants` / `selectSecondVariant`, ze Service `applyBatteryVariant`. Alt+8 je registrované i na vleku bez dronu (hláška „Na plošině není
dron“). Uložení: `.pad(?)#drone`, `#batteryVariant`, `#configDrone`. Síť: plošiny a typ baterií na začátku `writeState`.

**Rizika a co zbývá pro etapu 1:**

1. **Parametry letu jsou sdílené** (`SprayDroneFields.shared`): na Maxu proto obě plošiny musí mít stejnou velikost a dron 2 jde jen s dronem 1
   (`sdt_pad_mixed`, `sdt_pad_needFirst`). Hráč, který na Max položí S a L, dostane odmítnutí. Odstranit to znamená přesunout ~20 polí varianty
   (`tankCapacity`, `workWidth`, `droneMass`, `batteryCapacity`, rychlosti, `sprayMaxWind`, `pumpRate`, `maxRange` …) do per-drone seznamu a projít
   plánovač (`splitLegs` dělí práci podle odhadu času obou dronů) a baterie (jeden fond, jeden typ). Doporučuji zatím omezení nechat.
2. **Výměna jen na složeném vleku**: dron se dnes skládá jen se skládáním vleku. Sundat dron z rozloženého vleku by chtělo vlastní složení
   jednoho dronu (animace `foldParts` jde jen z času vleku). Na prázdnou plošinu rozloženého vleku dron položit jde, rozloží se hned.
3. **Náplň dronu se při výměně zahodí** (L se 75 l → M s 0 l). Etapa 1 ji musí nést v předmětu (`droneFillLevel`, `droneFillType`).
4. **Baterie mění typ s dronem** (nabití v podílu, model nové velikosti); u prázdné plošiny zůstává typ posledního dronu. Skutečné baterie
   různé velikosti jsou etapa 2.
5. **Jen v `onLoad` a při výměně se nepřenačítá**: `objectChange` konfigurace (viditelnost kořenů a úchytů přebíjí `setVisibility` výměny – funguje,
   ale konfigurace obchodu dál ukazuje původní dron), `workingWidth` v obchodě, `createStandInRoot` (náhradní kořen při chybějícím modelu by se
   při každé výměně vyrobil znovu), seznam kamer v `enterable` (kamera vyřazeného dronu zůstane pod skrytým uzlem; Alt+9 i kamera C s tím
   neověřené), nastavení „Drony v misi“ se po výměně vrátí na počet dronů.
6. **MP**: proud ověřen zkouškou bez druhého počítače (`padStream`), skutečný multiplayer ne. Výměnu zatím spouští jen server – etapa 1 potřebuje
   event od klienta (vzor `SprayDronePumpSlotEvent`).
7. **Prázdná plošina u Mini** neověřena (bedna `SprayDronePad` s dronem uvnitř).

## 10. Skenovací dron jako samostatný typ (2026-10-28, návrh)

Pavlovo zadání: sken nemá být režim postřikového dronu, ale vlastní dron. Dnes je sken „postřikový dron s prázdnou nádrží a nastavením
`missionMode = 1`“ (`SprayDroneStation.lua:77`, `getIsScanMode`, `applyMissionMode`). Prázdný dron letí zhruba třikrát déle jen proto, že je lehký
(`getFlightParams`, `planMass`) – to je náhodný vedlejší efekt, ne vlastnost skeneru.

### Čím se skenovací dron liší

| | postřikový S / M / L | skenovací |
|---|---|---|
| nádrž, čerpadlo, hadice, hrdlo | ano | **ne** (`tankCapacity = 0`, bez hadice a plnění, Alt+1 nemá co vypouštět) |
| mise | postřik / vápno | **jen sken** (`missionMode` se z typu odvodí, ne z nastavení) |
| hmotnost | podle varianty + náplň | vlastní, nízká (8 kg + S baterie 6,6 kg) |
| výdrž baterie a dosah | podle varianty | vlastní: delší výdrž, strop dosahu vyšší (nesou ho parametry typu, ne hmotnost náplně) |
| rychlost a výška | z úrovně skenu (`SprayDroneScanMap.LEVELS`) | totéž, `scanSpeed` a `scanMaxWind` z bloku typu |
| baterie | S / M / L | **stejná jako S** (jedna velikost, sdílí fond s postřikovým S) |
| RTK | ano | ano (rezerva v kroku 2 se čte z plošiny, stejně jako dnes) |
| model | tři velikosti | jeden: odvozený z S, bez nádrže a trysek, s kamerou / senzorem pod trupem a jinou barvou |
| cena | 7 000 / 12 000 / 22 000 € | návrh 6 000 € |

### Dopady na kód

Ověřeno čtením, ne ve hře.

1. **Nová varianta v `PAD_NAMES`** (`{ "S", "M", "L", "K" }`; písmeno K volím jen jako zkratku, jméno se dá změnit). `PAD_BITS = 2` pojme indexy 0–3,
   se čtyřmi typy plus prázdnou plošinou je potřeba **3 bity** (`SprayDronePadDrone.lua:129`, `writePads` / `readPads`).
2. **Blok `<drone name="K" prefix=...>`** ve vozidlech (`VARIANT_FLOATS`, `SprayDroneStation.lua:144`) s `tankCapacity="0"`. Na nulovou nádrž je kód citlivý:
   `getRouteStartFill` při skenu nastavuje `fill = tankCapacity` a pak odmítá `fill < 0.5` (`:3306-3312`), plánování dělí `tankCapacity` (`:2520`).
   Dnešní „plánuje se s plnou nádrží, spotřeba přípravku je nulová“ se tím pro sken zruší úplně: dávka je omezená jen baterií.
3. **Typ baterie je oddělený od jména dronu.** `PAD_NAMES` se dnes používá i pro `batteryVariant`. Blok typu proto dostane `batteryVariant="S"`
   a skenovací dron používá S baterie; nová velikost baterie není potřeba.
4. **`missionMode` z typu.** Pro skenovací dron je pevně 1 a nastavení „Mise“ v plánovači se skryje; u postřikového dronu je pevně 0 a skryje se i nastavení
   `scanCell` (hustota skenu patří jen skeneru). Postřikový dron už skenovat neumí. Zpětná kompatibilita se podle pravidel projektu neřeší, ladicí
   příkazy `scanMode` / `sprayMode` se přepíšou na `pad1K`.
5. **Plánovač a HUD**: u dronu bez nádrže se schovají řádky přípravku, litrů, doplňování a hadice; zůstane „Sken: buňka, výška, záběr“ a souhrn mapy.
   Stav „skenuje pole“ zůstává. `getDrainBlockReason` dostane důvod „dron nemá nádrž“.
6. **Servis na plošině**: plnění čerpadlem a mixér se pro dron bez nádrže přeskočí; zůstává přistání, výměna baterie a nabíjení.
7. **Savegame a MP**: `.pad(?)#drone="K"` a rozšířený `PAD_BITS`; mapa polí (`sdtScanMaps.xml`, `SprayDroneScanEvent`) se nemění.

### Míchání typů na Maxu

Etapa 0 zakazuje různé varianty na dvou plošinách (`sdt_pad_mixed`, `sdt_pad_needFirst`), protože parametry letu jsou sdílené (`SprayDroneFields.shared`,
~20 polí). U skeneru by to znamenalo, že Max nemůže mít jeden dron skenovací a druhý postřikový.

- **Doporučuji pro první verzi omezení nechat.** Mapa polí je na farmu, ne na vlek, takže skenovací dron na Minimu a postřikový na Middlu / Maxu
  spolupracují přes mapu bez míchání na jednom vleku.
- Až bude míchání potřeba, je to totéž přesunutí polí do per-dron seznamu, které už etapa 0 popisuje v rizicích. `missionMode` pak musí být per-dron a plánovač
  (`splitLegs`) dělit práci jen mezi drony stejné mise.

### Upravené pořadí etap

Skenovací dron jde jako čtvrtá varianta **už teď**, bez dronového předmětu a obchodu, na ladicím příkazu etapy 0:

| Etapa | Obsah | Ověření ve hře |
|---|---|---|
| 0b | Skenovací varianta `K` (model z S bez nádrže, blok v XML, parametry, schování postřikových voleb, 3 bity v síti); dočasně i jako volba konfigurace dronu v obchodě | `pad1K` na Middle a Mini: let, sken pole, mapa, uložení a načtení, plánovač bez nádrže |
| 1 | Dronový předmět (S / M / L / skenovací, náplň, RTK, usazení / sundání R) | koupit, nést, usadit, letět, sundat |
| 2–3 | beze změny (baterie jako předmět, konec konfigurací) | beze změny |

Etapa 4 z tabulky v kap. 6 tím odpadá: skenovací dron se řeší hned, ne až po předmětech. Dočasná konfigurace v obchodě se v etapě 3 zahodí s ostatními.

### Otevřené otázky pro Pavla

1. **Má postřikový dron po rozdělení ztratit sken úplně?** Doporučuji ano (jinak nikdo skenovací dron nepotřebuje).
2. **Skenovací dron používá S baterii** (sdílený fond), nebo má mít vlastní? Doporučuji S.
3. **Míchání na Maxu** (jeden skenovací, druhý postřikový) zatím ne? Doporučuji ne, viz výše.
4. **Vzhled**: jedna velikost odvozená z S bez nádrže, s kamerou pod trupem, jiná barva (např. šedá s oranžovými raménky)? Cena 6 000 €?
5. **Dočasně dát skenovací dron i jako volbu konfigurace v obchodě** (etapa 0b), abys ho mohl hned koupit s vlekem a vyzkoušet?

### Rozhodnutí Pavla (2026-10-28)

1. Postřikový dron po rozdělení **skenovat neumí**; sken je jen u skenovacího dronu.
2. Skenovací dron používá **S baterii** (sdílený fond s postřikovým S).
3. Míchání typů na jednom vleku (Max) **zatím ne**.
4. Vzhled a cena podle návrhu: jedna velikost odvozená z S, bez nádrže, kamera pod trupem, jiná barva; 6 000 €.
5. **Žádná dočasná volba v obchodě.** Skenovací dron se až do etapy 1 zkouší jen ladicím příkazem `pad1K`.

### Stav etapy 0b (2026-10-28): napsáno, ve hře neověřeno

Hotové (statické kontroly `tools/check_all.py --no-build` stejné jako před změnou, `lua_check` a `audit_spec_fields` OK, offline plán `tmp/test_scan_plan.py`):

- Varianta **K** v `PAD_NAMES`, `PAD_BITS = 3`; bloky `<drone name="K" scan="true" batteryVariant="S" tankCapacity="0" droneMass="8" maxRange="600" scanSpeed="12" scanMaxWind="12">`
  ve všech třech vlecích (u Maxu i pro slot 2). **Model, uzly a zvuky jsou zatím z dronu S** (včetně hadice a trysek), vzhled K se dělá později.
- `spec.isScanDrone` z atributu `#scan`; `applyMissionMode` z něj odvozuje `missionMode` (K = sken, S/M/L = postřik), nastavení „Mise“ je v plánovači trvale šedé
  (`isSettingEnabled`) a ukazuje, co dron dělá. `scanCell` tím zůstává jen u skeneru, `applyMode` (aplikace podle skenu) jen u postřikového dronu.
- `SprayDroneStation.getPlanTank`: plán trasy skeneru počítá s nádrží `SCAN_PLAN_TANK` (100 000 l) a nulovou hmotností náplně; fyzická nádrž je 0.
- `scanSpeed` a `scanMaxWind` se čtou z bloku varianty (`VARIANT_FLOATS`), baterie z bloku varianty `batteryVariant` (S).
- HUD a karta plánovače pro dron bez nádrže ukazují jen baterii; překlad `sdt_drone_K` (cz/en/de).
- Ladicí příkazy `pad1K` a `pad2K`; `scanMode` / `sprayMode` mód už nepřepínají (jen to napíšou do logu).

Nezkoušeno ve hře, na co se podívat: `pad1K` na Middle (načtení bez chyby v logu, plánovač „Sken: …“ bez řádků nádrže a přípravku, let a sken pole, mapa, výdrž na jedné
baterii zhruba 3× delší než S, uložení a načtení se `.pad#drone="K"`); Mini s prázdnou bednou; Max `pad1K` + `pad2K` a odmítnutí smíšené dvojice (`sdt_pad_mixed`).
Model K je hotový a vyexportovaný (2026-10-28, `blender/build_drone.py`: `SPECS["K"]` = geometrie S, tmavý trup, oranžové kryty ramen, kardanový podvěs s RGB čočkou a čtyřmi multispektrálními místo nádrže, čerpadla a trysek; prefixy `Drone_K_` / `Drone2_K_`, hidden v i3d). Bloky `<drone name="K">` jsou v šablonách `blender/templates/*.xml.in` (vozidlová XML se z nich při exportu generují, ruční úpravy v `vehicles/*.xml` se přepíšou). Mini, Middle i Max přestavěné a exportované, `check_xml_nodes` OK. Zbývá: ve hře ověřit (viz výš) a plnicí hrdlo se u K nestaví (uzel `FillPort` zůstává kvůli kontraktu), hadice vleku je tedy jen na vleku. Polepy značky na trupu K nejsou.

## 11. Precision Farming: dron jako „Isaria“ (2026-10-28, návrh, Pavel souhlasil se zápisem; neimplementováno)

Nápad Pavla: dron by měl umět to, co crop senzor Isaria z Precision Farming (PF) na traktoru. Isaria měří biomasu a stav dusíku v porostu a podle toho za jízdy mění dávku hnojiva
na připojeném stroji (zdroj: výsledky hledání a diskuse na Steamu, wiki stránka se nenačetla, přesnou logiku ve FS25 jsem nečetl).

**Dnešní stav** (`SprayDroneStation.lua`): postřikový dron při hnojení a vápnění zapisuje do map PF (dusík, pH) pevnou dávkou (`applyPrecisionFarming`, `getPrecisionFarming`);
skenovací mapa PF nečte (jen vanilla `FieldState`); větve pro PF jsou ve hře neověřené. Přepočet stavů mapy na l/ha v plánovači je připravený (`SprayDroneRoute.lua`, „Precision Farming:
kolik stavů mapy odpovídá pevné dávce“).

**Dvě části, nezávislé:**
1. **Skenovací dron `K` jako Isaria z výšky**: do skenovací mapy (`SprayDroneScanMap.FIELDS`) přibydou vrstvy z PF (dusík, cílový dusík, pH, typ půdy), pokud je PF načtené.
2. **Postřikový dron s proměnnou dávkou**: režim „aplikace podle skenu“ (`applyMode`) dnes rozhoduje jen, kam se stříká; nově i kolik na buňku, z rozdílu cíle a stavu.
   Dron by dávku měnil rychlostí letu nebo průtokem; to je nejtěžší část (dnes je dávka pevná na celý let).
3. Bez PF zůstává vše jako dnes; mod na PF nesmí záviset.

**Hlavní nejistota:** jestli PF pustí cizí mod k svým mapám přes `g_precisionFarming` (PF je interní mod, proměnná žije v jeho prostředí; ladicí příkaz `SprayDroneDebug` s výpisem funkcí PF existuje).

**Etapa 0c (až po ověření `pad1K` ve hře):** malý pokus bez změny chování: skenovací dron při letu vypíše do logu dusík a pH ze středu každé buňky; do `SprayDroneScanMap.sampleCell` přibude jen čtení za podmínkou
`getPrecisionFarming() ~= nil`. Když vrátí smysluplná čísla, pokračuje část 1 (vrstvy v mapě, plánovač, překryv na mapě), potom část 2. Když ne, zapsat důvod sem a PF z návrhu vyřadit.

## 12. Etapa 1: dron jako předmět (2026-10-28, napsáno, ve hře neověřeno)

Pavel: „tak to implementuj“ (po zjištění, že drony se kupují jen s vlekem). Hotové:

- **Vlek se kupuje bez dronu**: konfigurace `sprayDrone` je pryč (kód, schéma, šablony `*.xml.in` i vozidlová XML, `#configDrone` v savegame); plošiny jsou po nákupu prázdné.
  Typ baterií prázdné plošiny je výchozí `M`, na Minimu (varianty S a K) první varianta bloku (`selectPadVariants`).
- **Dronové předměty** `objects/drone/drone{S,M,L,K}.xml` (vehicle type `sdtDrone` = pallet + `SprayDroneItem`), ceny 7 000 / 12 000 / 22 000 / 6 000 €, kategorie BZUK vybavení, v obchodě.
  Model je složený dron (`blender/build_drone_items.py`, ramena podél trupu, listy složené, bez polepů). Náplň nese obyčejný fill unit 1 (K ho má jen formálně, kapacita 1).
- **Plošina jako slot** (`scripts/SprayDronePadSlots.lua`, `events/SprayDronePadSlotEvent.lua`): R u prázdné plošiny s dronem v ruce (nebo ležícím do 2,5 m) dron nasadí
  (`SprayDroneStation.setPadDrone` z etapy 0, náplň se přenese do dronu), R bez dronu v ruce u obsazené plošiny ho sundá (vyrobí se předmět s náplní; plošina se uvolní až po
  úspěšném načtení). Podmínky jsou ty z etapy 0: nic neletí, vlek je složený (sundání), obě plošiny Maxu stejné velikosti. Mini: dron jde nasadit i sundat při zavřené bedně (vlek složený), stejná podmínka jako u ostatních vleků.
- **Síť**: stav plošin už jde v `writePads`, příkaz z klienta jde eventem (vzor `SprayDronePumpSlotEvent`), server kontroluje farmu a vzdálenost.

**Odchylky od návrhu:** baterie v dronu se při sundání vrací do nabíječky vleku (předmět nese jen náplň; baterie jako předmět je etapa 2); RTK zůstává konfigurací vleku (etapa 3);
polepy na předmětu nejsou.

**Na co se podívat ve hře:** koupit dron S/M/L/K v obchodě; R u plošiny (drží se v ruce, i ležící); nasazení na složený i rozložený vlek (rozložený: dron se rozloží hned);
sundání jen ze složeného vleku; náplň se přenese tam i zpět; Max se dvěma stejnými drony a odmítnutí různých; Mini s bednou; uložení a načtení; složený dron M a L je 2,3 a 2,6 m široký,
nošení v rukou může vypadat divně (alternativa: nosit jen na korbě).

### Úprava 2026-10-29 (Pavel, docs/PLAN-airasi-kufr.md F1 bod 5; napsáno, ve hře neověřeno) – mění podmínky výše

- **Sundání z rozloženého vleku (Middle, Max, Mini):** R u obsazené plošiny dron nejdřív složí a teprve pak z něj udělá předmět. Per-drone pole `foldHold`
  (SprayDroneFields, jde klientům ve `writePads` jako jeden bit na plošinu) dává cíl rozložení 0 (`SprayDroneStation.getDroneUnfoldTarget`, dorovnání
  v `updateDroneParts`); server si sundání pamatuje v `padSlots.folding` a v `SprayDronePadSlots.update` počká, až je `unfold == 0`, vrtule dotočené,
  hadice namotaná a baterie dojela do nabíječky (se složením odchází sama, `updateBatteryPlacement`). Pak se vyrobí předmět jako dřív (`ps.spawning`);
  `foldHold` se maže těsně před `setPadDrone`. Zruší se (dron se zase rozloží podle vleku), když se mezitím něco rozběhne (`getTakeProblem`), plošina se
  změní nebo to trvá déle než 20 s. Během skládání nejde spustit misi (`startDrone`, `getCanStart`), vypustit dron (`getCanTransfer`), vzít baterii do
  dronu ani vyměnit dron na druhé plošině (`getPadBlocker`: `foldHold` = obsluha). Hadice se odpojí sama (`connect` chce `unfold >= 1`).
- **Mini: nasadit i sundat jen u rozložené bedny** (`getPadBlocker`: `SprayDronePad.getDeploy < 1` → `sdt_pad_boxStowed`). Dřív to bylo naopak jen proto, že
  platila obecná podmínka „dron musí být složený“ a dron na Minimu je složený jen v zavřené bedně (rozkládá se na plošině, `trailerFoldEnd` = `pad#foldEnd`);
  do zavřené bedny se ale dron vkládat nedá. Na rozloženou plošinu se dron nasadí a hned rozloží (jako u ostatních vleků), při sundání se složí (foldHold).
  Když se bedna během skládání začne zavírat, sundání se zruší.
- **Mini v obchodě složený** (`SprayDronePad.openInShop` už nenastavuje `shopPose`; půl-otevřená bedna jde jen ladicím příkazem `shopPose`).
- **Obchod:** nová kategorie `sprayDroneDrones` „Drony“ v záložce BZUK (ikona `objects/drone/store_droneM.dds`): drony S/M/L/K a tablet (ten zůstává i
  v `handtoolsMisc`). Baterie jako předmět zatím není (etapa 2), až bude, patří sem taky.

**Na co se podívat ve hře:** sundání z rozloženého Middle/Max (ramena a listy se složí, pak předmět; baterie dojede do nabíječky); pokus o start mise během skládání;
Max se dvěma drony (sundat jde jen dron 2, pak 1); Mini: R u zavřené bedny hlásí „jen u rozložené bedny“, u rozložené nasadí (dron se rozloží) i sundá (složí se);
kam se u Mini vyrobí předmět, když hráč stojí za vlekem u plošiny (může padnout na plošinu); MP klient vidí skládání; obchod: Mini složený, záložka Drony.

**Odepnutí na místě (Pavel 2026-10-29 večer, ve hře neověřeno):** „R pro odpojení dronu od vleku – dron se jen složí a odepne, jinak zůstane na místě.“
Předmět už nevzniká na zemi u hráče: `SprayDronePadSlots.getTakePose` ho postaví přesně na místo složeného dronu (kořen `<prefix>Root`, resp. `drone.node`),
jen o `TAKE_LIFT` 5 cm výš (kolize desky Mini sahá 3 cm nad povrch, paluba Middle/Max je 5 mm pod lyžinami) a otočený o `ITEM_YAW` −90° (nos dronu
míří v kořeni na vleku po +Z i3d, v předmětu po +X). Platí pro Middle, Max (obě plošiny) i Mini (bedna i plošina; u rozložené bedny dron leží na otevřené
palubě, stěny bedny jsou sklopené a kolize nemají). Text akce „Odepnout dron (%s)“.

### Úprava 2026-10-29 odpoledne: Mini – dron má dvě polohy a nepřesouvá se sám (napsáno, ve hře neověřeno)

Pavel: „A u mini neposouvat automaticky drona, ale nechat to na ruční práci. Takže dron má dvě polohy, z jedné ho vezmu a do druhé vložím.
Vlek se nemůže složit, pokud je na rozložené pozici dron.“ Mění bod „Mini“ výše:

- **Polohy** (`spec.pad.onPlate`): A = přepravní, v bedně na palubě (uzel `droneCarrier`, jak je v i3d, tj. dnešní složená póza; nový uzel ani
  export netřeba), B = letová, na středu rozložené plošiny (`plan.centerLocal` − `droneSettle`, otočený do letové osy). `SprayDronePad.applyPose`
  dron s bednou nehýbe, staví carrier podle `onPlate` (B jen s rozloženou bednou); fáze „nadzvednout, otočit, přejet“ (`LIFT_END`, `MOVE_END`) je pryč.
- **Přendání jen ručně, jako předmět:** R u polohy, kde dron stojí, ho vezme (rozložený se nejdřív složí, `foldHold`); R s dronem v ruce u volné polohy
  ho vloží do bližší z nich (`SprayDronePadSlots.getSpots`, příkaz `PLACE` = bedna / `PLACE_PLATE` = plošina, `CMD_BITS` 2). Obě polohy jen
  u rozložené bedny (zavřenou bednou se k dronu nedostane, `sdt_pad_boxStowed`); u složené se nabízí jen místo v bedně (s hláškou).
- **Dron v bedně** zůstává složený (`getDroneUnfoldTarget` = 0, `initDroneFold` bere cíl odtud) a nevzlétne: `startDrone`, `getCanStart`
  a `getFoldedWarning` → `sdt_planner_droneInBox` „Dron je uložený v bedně – přendej ho na plošinu“ (start i čip v plánovači).
- **Složení vleku** s dronem na plošině nejde (`getIsFoldAllowed`, směr > 0 → `sdt_warning_padDroneOnPlate` „Nejdřív přendej dron do bedny“);
  dron v bedně složení nebrání. Rozložení vleku dron nechá v bedně.
- **Uložení a síť:** `pad(0)#onPlate` v savegame; stará hra bez atributu → plošina, je-li dron a bedna úplně rozložená, jinak bedna
  (`SprayDronePad.getLoadedOnPlate`). Ve `writePads` jeden bit navíc (jen vlek s bednou), klient ho nastaví před přenačtením dronu.
- **Ladění:** `padMiniInfo` (poloha, bedna, cíl rozložení, start, složit / rozložit), `padMiniStow` / `padMiniDeploy` (přendá dron bez hráče,
  okamžitě; `SprayDronePadSlots.debugMoveMini`). Offline test `tools/test_mini_pad.py`.

**Zbývá:** při rozkládání je po vyrovnání plošiny (D 0,53–1) klidová pauza (dřív v ní jezdil dron). Úvodní 2 s skládání pryč (viz úprava „noc“ níž).

**Na co se podívat ve hře:** rozložit Mini s dronem → dron zůstane v bedně složený, R „Sundat“ u bedny, R s dronem v ruce za vlekem „Postavit dron
na plošinu“ (rozloží se), složit vlek → „Nejdřív přendej dron do bedny“; zpět do bedny („Uložit dron do bedny“), složit jde; start / plánovač s dronem
v bedně; uložení a načtení v obou polohách; stará hra s rozloženým Mini; MP klient vidí polohu.

### Úprava 2026-10-29 večer: bod u bedny Mini, přendání R, hadice jen u postřikového dronu (napsáno, ve hře neověřeno)

Pavel: „Když na Mini mám předělat drona ‚do bedny‘, měl by tam být bod, který to chytne.“ a „Bez dronu pro postřik nebude vidět hadice.“

- **Body pro R:** `SprayDronePad.load` vytvoří za běhu dva uzly pod rodičem bedny, `sdtPadBoxPoint` (místo dronu v bedně + `POINT_LIFT` 0,3 m)
  a `sdtPadPlatePoint` (střed plošiny, posouvá `applyPose`); i3d ani export se nemění. Míření na bod dává obvyklý bonus `SprayDroneLink.aimDistance`
  (dřív se mířilo na `padAnchor` / `padHingeH`, tedy na hranu paluby a čep, ne na bednu).
- **Bedna chytá:** do `SprayDronePadSlots.BOX_CATCH_DISTANCE` (1,5 m vodorovně od bedny) patří R bedně, i když je hráč blíž středu plošiny (ten je
  od bedny 2,2 m). S dronem v ruce hlásí plošina vzdálenost 0, takže R nepřebije bedna na kanystry, hrdla ani hadice.
- **Přendání R s prázdnýma rukama:** u rozložené bedny nabízí obsazená plošina i druhé místo (`getSpots` → `move`): u bedny „Přendat dron do bedny“
  (`sdt_padslot_moveBox`), u plošiny „Přendat dron na plošinu“ (`sdt_padslot_movePlate`). Příkazy `MOVE_BOX` / `MOVE_PLATE` (`CMD_BITS` 3, bez předmětu),
  server `SprayDronePadSlots.moveMiniTo` (od úpravy „noc“ okamžitě, totéž co ladicí `padMiniStow` / `padMiniDeploy`). R u místa, kde dron stojí,
  ho dál vezme jako předmět.
- **Hadice:** odvinutá hadice (články + koncovka) jen u rozloženého **postřikového** dronu (`hose.spray` = `SprayDroneStation.getHasSprayDrone`: dron
  na plošině a varianta bez `#scan`). Prázdná plošina, skenovací dron i dron v bedně Mini → hadice namotaná na navíječi (`…Coil` vidět). Výměna za hry
  i klient jdou přes `loadDroneService` (nová hadice, první update ji srovná). Max s prázdnou plošinou 2 po načtení: `SprayDroneStation.stowSecondPad`
  schová hadici B a úchyty 2 (dřív zůstaly vidět, jak jsou v i3d, i navíječ s hadicí najednou).

**Na co se podívat ve hře:** Mini rozložený s dronem na plošině, stát u boku / zadní hrany bedny → „Přendat dron do bedny“, dron je hned složený v bedně;
za vlekem u plošiny → „Přendat dron na plošinu“; s dronem v ruce u bedny vedle bedny na kanystry → „Uložit dron do bedny“; Middle/Max/Mini rozložený
bez dronu → jen navíječ, žádná hadice na desce; nasadit S → hadice se odvine; Max s jedním dronem po načtení → hadice B jen na navíječi; MP klient totéž.

### Úprava 2026-10-29 noc: přendání na Mini bez animace, kratší skládání (napsáno, ve hře neověřeno)

Pavel: „Mini má pořád při skládání hrozně dlouhou sekvenci, kdy se snaží dostat dron z přistávací plochy do bedny. … Radši tu animaci vymaž
a nepoužívej.“

- **Přendání R je okamžité:** `moveMiniTo` už dron neskládá přes `foldHold` a nečeká v `SprayDronePadSlots.update` (pole `moveTo` pryč), rovnou
  volá `SprayDronePad.setDroneOnPlate`. Ta (server i klient z `readPads`) nastaví dronu 1 `unfold` na cíl (`getDroneUnfoldTarget`: bedna 0,
  plošina 1), zastaví a srovná vrtule (`rotorSpeed` 0, úhel 0) a hadici namotá (`hoseT` 0). Baterii z dronu v bedně vrátí do slotu obvyklé
  `updateBatteryPlacement`. Samostatná animace ramen se při přendání nepouští (ani rychlá): dron se objeví rovnou v cílové póze, jinak by
  „přendání“ zase vypadalo jako přesun.
- **Skládání vleku** s dronem na plošině dál odmítne `getIsFoldAllowed` hláškou „Nejdřív přendej dron do bedny“; rozložení dron na plošinu nedává.
- **Animace `foldTrailer` 12 → 10 s:** úvodní rezerva na složení dronu (0–2,6 s) zkrácena na 0,6 s, ostatní časy (víko, světla, zvuky) o 2 s dřív;
  `pad foldStart/foldEnd` 0,86 / 0,06, `trailerFoldEnd` 0,06, `securedFoldTime` 0,9 (export z `build_trailer_mini.py`: `FOLD_DURATION`,
  `DRONE_UNFOLD_TIME`, `CLAMP_TIME`, `LID_TIME`, `PAD_REAR_TIME`; model se nemění). Vedlejší efekt: složení dronu před sundáním z plošiny
  (`foldHold`, TAKE) trvá na Mini ~0,4 s místo ~1,7 s. Middle a Max beze změny.
- **Na co se podívat ve hře:** X s dronem na plošině → hláška; R „Přendat dron do bedny“ → dron hned v bedně složený, X → bedna se složí bez
  pauzy na začátku; R „Přendat dron na plošinu“ → dron hned rozložený na plošině; uložit a načíst v obou polohách; MP klient vidí přendání hned.

## 13. Baterie jako předměty (F4, 2026-10-29, napsáno, ve hře neověřeno)

Zadání: docs/PLAN-airasi-kufr.md F4 a D1. Hotové:

- **Předmět** `objects/battery/battery{S,M,L,C,P}.xml` (vehicle type `sdtBattery` = pallet + `SprayDroneItem` s `#battery`): velikost podle typu baterií vozidla
  (`spec.batteryVariant`: S/M/L vleky, C kufr skenovacího dronu, P kufr AIRASI), nabití ve fill unitu 1 (ELECTRICCHARGE 0..100 %, savegame i síť řeší vanilla
  FillUnit, HUD ho ukazuje při nesení), diody `batteryLed0..3` po čtvrtinách (`SprayDroneItem.updateLeds`). Hmotnosti 6,6 / 12,1 / 14,7 / 0,35 / 1,1 kg, `supportsPickUp`.
  Obchod: kategorie `sprayDroneDrones`, S/M/L 1 500 € (= dnešní cena za kus v konfiguraci), C 250 €, P 600 €.
- **Šachta = slot poolu** (`scripts/SprayDroneBatterySlots.lua`, `events/SprayDroneBatterySlotEvent.lua`): R s baterií v ruce u šachty ji vloží (první volná nejblíž,
  velikost musí sedět), R bez ničeho u obsazené šachty ji vyndá (předmět se vyrobí u hráče jako u plošiny, z poolu zmizí až po načtení). Jen na rozloženém vleku
  / s otevřeným víkem kufru. U kufru se vyndává i baterie z dronu, který v kufru sedí (`getIsDroneIdle`: doma, PARKED, ne mise, výměna, skládání), a jen do 1 m od
  baterie, dál R ovládá víko. U vleku se z dronu baterie R nevyndává (u plošiny je R „sundat dron“), jen ladicím `batteryTake d1`.
- **Pool s dírami = proměnný počet** (nejmenší zásah): `spec.batteries` zůstává pole `{charge, slot, drone}`, jen se mění jeho délka
  (`SprayDroneStation.setBatteryCount`, `addBattery`, `removeBattery`; odebrání posune `droneBattery` dronů a srovná modely v šachtách bez animace). Prázdná šachta =
  žádná baterie s tím `slot`. Strop je `numBatterySlots` **i s baterií v dronu** (ta se při skládání vrací do šachty, `getFreeBatterySlot` jinak nemá kam) – u kufru
  (jedna šachta) je tedy jedna baterie, buď v šachtě, nebo v dronu. Výměna při servisu (`swapBattery`, `getBestSlottedBattery`) a vrácení do šachty s dírami počítaly
  už předtím; bez baterií start nejde (`startFlight`, `getCanStart`, čip v plánovači `sdt_warning_noBatteries`), dron bez nabité baterie čeká (`swapPending`).
- **Konfigurace počtu baterií** v obchodě vleku zůstává: předplní šachty při koupi (`spec.batteryConfigCount`). Savegame ukládá všechny baterie a `#batteryConfig`;
  po načtení platí uložený počet, změna konfigurace v dílně ho posune o rozdíl.
- **Síť**: `writeState` posílá počet baterií (`batterySlotBits`) před pool, klient srovná délku (`setBatteryCount`).
- **Podezření z testu F2 potvrzené a opravené**: let vybíjí jen `spec.battery` dronu, do poolu se nabití zapisovalo až při vrácení do šachty, uložení a odeslání
  stavu. Kufr po přistání (víko otevřené, baterie v dronu) proto v HUD, diodách a `caseInfo` ukazoval nabití ze vzletu, nenabíjel se (pool „plný“) a kdyby pool plný
  nebyl, nabíjení by do dronu zapsalo staré nabití zpět. `SprayDroneCase.updatePower` teď na začátku srovná pool z dronu (`syncDroneBatteryCharge`).
- Opraveno mimochodem: `SprayDronePadSlots.doPlace` volal `markRouteDirty` se spec místo vozidla (chyba v Lua po nasazení dronu, předmět by se nesmazal).
- Ladění (`SprayDroneDebug.batteryCommand`): `batteryInfo`, `batteryTake [n|d1|d2]`, `batteryPut`, `batterySpawn S|M|L|C|P`. Offline test `tools/test_batteries.py`
  (v `check_all`).

**Otevřené:** typ baterií vleku se dál mění s dronem na plošině (`reloadFirstDrone`: baterie v šachtách si nechají procenta a změní velikost) – vlek koupený
s předplněnými M bateriemi a dronem S by jinak měl nepoužitelné baterie. Pokud má platit „baterie má pevnou velikost“, musí nasazení dronu jiné velikosti na vlek
s bateriemi skončit odmítnutím. Předmět jde zatím jen vyrobit u hráče na zem, ne rovnou do ruky.

**Na co se podívat ve hře:** koupě baterií v obchodě (záložka Drony, obrázky, cena, hmotnost v ruce); R u šachty Middle/Max/Mini (vyndat, vložit, jiná velikost,
plno, složený vlek); model v šachtě zmizí / objeví se; nabití předmětu a diody; uložení a načtení (počet, nabití, předmět s nabitím); kufr: vyndat baterii z dronu
zblízka, R dál od kufru zavírá víko, vložit C do prázdného kufru; mise bez baterie se nespustí; MP klient (počet baterií, event).
