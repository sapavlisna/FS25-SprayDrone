# Jak mají fungovat hadice

Cílový popis chování (spec), ne historie. Sepsáno podle kódu k 2026-10-28 (`SprayDroneWaterHose.lua`, `SprayDroneHoseLib.lua`, `SprayDronePump.lua`,
`SprayDroneMill.lua`, `SprayDroneHopper.lua`, XML vozidel, Blender skripty). Co je v kódu jinak, než jak to tu stojí, je v sekci 5.

## 1. Přehled hadic

| hadice | kde začíná | délka | průtok | zdroj / cíl |
|---|---|---|---|---|
| **vlek (Middle, Max)** – jedna hadice na vozidlo | spojka na vleku podle toho, u které stojíš: ventil vodní nádrže (Middle 5 ventilů 800–5000 l, Max 4: 3000, 3000B, 5000, 5000B; viditelné jsou jen ventily nainstalované konfigurace), nebo vstup nádobky na koncentrát | 12 m (72 článků) | voda 12 l/s | voda: IBC, cisterna, jiný vlek s vodou (dovnitř), případně do prázdné cizí nádrže (ven); vápno: výstup mlýnku nebo násypky |
| **pumpa – VSTUP** (modrá spirála, objímka modrá) | spojka `pumpInletPort` na boku pumpy | 10 m (60 článků) | 16 l/s | režim „nádrž“: IBC / cisterna / vlek s vodou; režim „rybník“: sací koš do vody |
| **pumpa – VÝSTUP** (červená spirála, objímka červená) | spojka `pumpOutletPort` na druhém boku | 12 m (72 článků) | 16 l/s | vodní ventil vleku, nebo libovolná cizí nádrž, která bere vodu |
| **vápno** = tatáž hadice vleku u vstupu na koncentrát | vstup nádobky na koncentrát (`limeInletNode`, fill unit 3) | 12 m | `min(12, hoseRate zdroje)` = 8 l/s | výstup mlýnku (`millOutletPort`) nebo násypky (`hopperOutletPort`) |

- **Mini nemá žádnou hadici** (nemá specializaci `sprayDroneWaterHose`). Pumpa mu ale může výstupem napustit vodu jako libovolné cizí nádrži.
- Hadice vleku je černá (`SDT_HoseBlack`), koncovka má červenou objímku. Pumpa má obě hadice spirálové, barvy podle spojek (vstup modrá, výstup červená).
- Pumpa (`waterPump.xml`): těleso čerpadla 200 l (fill unit 2), nafta 15 l (fill unit 1, 3 l/h), `minDepth` 0,15 m. Násypka na vápno používá stejný motor (`SprayDronePump`), ale hadice nemá;
  je jen zdrojem vápna (500 l, `hoseRate` 8).
- Mlýnek (`sdtLimeMill`) má `hoseRate` 8; s ventilem na výsypné rouře hadice zůstane připojená, ale nic nedostane (`getOutlet().closed`).
- Hadice jsou jen na vozidlech (specializace na vleku a na pumpě); mlýnek a násypka jsou pasivní zdroje s uzlem `outlet`.

## 2. Pravidla jednotlivých hadic

Společné: hadice je „venku“ (vytažená) nebo zasunutá. Venku je buď **nesená** (nese ji hráč), nebo **připojená** (druhý konec drží zdroj / cíl). Stav drží server.

### 2.1 Hadice vleku, voda (ventil vodní nádrže)

| | |
|---|---|
| Vzít | R u ventilu do `PORT_DISTANCE` 1,9 m (z hráče +1 m výš), ventil nesmí být obsazený (vlastní hadicí ani výstupní hadicí pumpy) |
| Připojit | koncem v ruce k zdroji s vodou (> 0,001 l v nějaké nádrži): **s vypouštěcím uzlem** (nízký, do `OUTLET_MAX_HEIGHT` 0,8 m nad počátkem) jen na něj, do `SOURCE_RADIUS` + `OUTLET_REACH` = 1,6 m od uzlu; **bez uzlu** kamkoli na karoserii do `SOURCE_RADIUS` 1,1 m od obdélníku `v.size` (vodorovně) |
| Směr toku | zdroj → nádrž vleku (`transfer`, `rate` 12 l/s), dokud je v zdroji voda a ve vleku místo |
| Opačně | zdroj bez vody, ale s volnou nádrží (prázdná cisterna / IBC) → hadice se připojí „napustit“ (`targetPort = TANK_ARG`) a teče **z vleku do ní**; směr se určí při připojení a už se nemění |
| Zdroj pumpy | pumpa se jako zdroj nepočítá; vlek z ní čerpá jen výstupní hadice pumpy |
| Podmínky toku | zdroj má vodu, nádrž vleku je prázdná nebo s vodou (jinak jednorázová hláška `sdt_wh_mixed`) |
| Nápověda | vzít „Vzít vodní hadici“ → v ruce „Připojit hadici ke zdroji vody“ / „…k nádrži (napustit vodu)“ / „Nádrž nemá vodu, nejde z ní čerpat – pustit hadici“ / „Pustit hadici“ → připojená „Odpojit vodní hadici“ |

### 2.2 Hadice vleku, vápno (vstup na koncentrát)

| | |
|---|---|
| Vzít | R u vstupu, text „Vzít hadici (vápno z mlýnku nebo násypky)“ |
| Připojit | k výstupu mlýnku (ne v režimu big bag) nebo násypky, který má jemné vápno (> 0,001 l), do 1,5 m (3D) od uzlu `outlet`; konec hadice sedí přesně na čele spojky výstupu |
| Směr toku | mlýnek / násypka → nádobka vleku (fill unit 3, `SDT_FINE_LIME`), max 8 l/s |
| Podmínky | zdroj **běží** (motor mlýnku / násypky) **a** kohout vstupu je **otevřený**; po každém připojení je kohout zavřený |
| Kohout | levé tlačítko myši u vstupu (text „Otevřít / Zavřít ventil“), páka `limeValveLever` se otočí o 90° za 0,35 s; stav se ukládá |
| Mlýnek | ventil jde přepnout na výsypnou rouru i s připojenou hadicí, ta pak nic nedostane (nápověda `sdt_mill_hoseSpout`); slepá spojka výstupu (`portCap`) se skryje |

### 2.3 Pumpa, VSTUP (jedna hadice, dva režimy)

| | |
|---|---|
| Režim | ručně přepíná levé tlačítko myši u vstupní spojky (do 1,9 m); text „Vstup na rybník (sací koš)“ / „Vstup na nádrž (spojka Storz)“; výchozí „nádrž“; ukládá se jen „rybník“ |
| Přepnout jde | jen se **stojícím motorem** a bez sací hadice připojené (nesená nebo odložená nevadí, nesená se při přepnutí odloží); jinak hláška `sdt_pump_modeEngineOn` / `sdt_pump_modeHoseAttached`; blokuje i klávesa X a předmět v rukou |
| Koncovka | „nádrž“: Storz; „rybník“: Storz + mosazný nátrubek + sací koš (`inStrainerEnd`) |
| Nádrž – připojit | stejné cíle jako 2.1, ale jen zdroje s vodou (pumpa nikdy „nenapouští“); text „Vzít sací hadici (IBC, cisterna)“ |
| Rybník – položit | koš v ruce se hodí do vody: pod rukou, jinak v kruzích 0,5 / 1,0 / `POND_REACH` 1,5 m kolem ruky (8 směrů); voda aspoň `minDepth` 0,15 m (paprsek `CollisionFlag.WATER`); koš leží 0,12 m nad dnem; text „Vzít sací hadici (koš do rybníka)“ → „Položit sací koš do vody“ |
| Rybník – za provozu | server každých 500 ms kontroluje, jestli je koš dál ve vodě; pak teče do tělesa pumpy |
| Směr toku | zdroj / rybník → těleso pumpy (fill unit 2), 16 l/s, **jen za chodu motoru** |

### 2.4 Pumpa, VÝSTUP

| | |
|---|---|
| Vzít | R u výstupní spojky, „Vzít výstupní hadici (do vleku)“ |
| Připojit | 1) **vodní ventil vleku** (druh `water`, neobsazený) do `SINK_RADIUS` 2,0 m (3D) od ventilu, text „Připojit hadici k vodnímu ventilu vleku“; 2) když žádný není, **cizí nádrž** (cisterna, IBC, postřikovač, Mini; ne vlek ani pumpa), která bere vodu, má kapacitu > 100 l, volné místo a je prázdná nebo s vodou, do 2,0 m od obdélníku `v.size`, text „Připojit hadici k nádrži (napustit vodu)“ |
| Směr toku | těleso pumpy → nádrž vleku / cizí nádrž, 16 l/s, **jen za chodu motoru** |
| Nápověda | pumpa po 1,5 s chodu bez toku ukáže „Pumpa nic nečerpá – zapoj hadice (vstup, výstup)“ (násypka toto varování nemá) |

### 2.5 Motor pumpy a násypky

B (`SDT_MILL_ENGINE_FOOT`) do `CONTROL_DISTANCE` 2,8 m od motoru zapne / vypne; bez nafty ne („Pumpa nemá naftu“). Nafta se spotřebovává za chodu, po vyčerpání se motor sám vypne.
Naftu nalévá kanystr nad hrdlo (`SprayDroneMill.updatePour`). Stav „čerpá se“ (zvuk toku) drží 400 ms po posledním přelití.

### 2.6 Společná pravidla

- **Utržení:** nesená hadice se utrhne, když je konec dál než délka hadice + 2 m od spojky; připojená, když je připojený konec dál než délka hadice od spojky (přímo, ne po trase) – „Vodní hadice se utrhla“. Ruka dosáhne nejdál na 0,95 délky.
- **Průtok** je omezen volným místem v cíli, množstvím ve zdroji a `rate` hadice (u vápna i `hoseRate` zdroje). Do nádrže s jiným přípravkem se nepřelévá (hláška jednou za připojení).
- Obsazenost: jeden ventil vleku nese jednu hadici (vlastní vleku, nebo výstup pumpy).

## 3. Ovládání

- **R (ACTIVATE_OBJECT)** je jediná klávesa pro hadici: vzít (u spojky) → nést → připojit (u zdroje / cíle) nebo pustit (jinde, hadice se zasune) → odpojit (u spojky do 1,9 m, nebo u druhého konce do 2,0 m).
  Nesená hadice má přednost před všemi ostatními R akcemi.
- **Levé tlačítko myši (ACTIVATE_HANDTOOL)** hadici nebere ani nepřipojuje. Dělá jen: kohout vstupu na koncentrát (u připojené hadice na vstupu vleku) a přepnutí režimu vstupu pumpy (u vstupní spojky, hadice odložená nebo připojená u spojky).
  Nefunguje s X nebo s předmětem v rukou. Mlýnek má vedle toho vlastní levý klik na páku ventilu (do 2,6 m): přepíná výstup hadice / výsypná roura.
- **B** zapíná motor pumpy / násypky (do 2,8 m), u mlýnku B u rozvaděče.
- **Víc aktivátorů vedle sebe:** hra nabídne vždy jen jeden, nejbližší podle `getDistance`. U vleku se tak perou hadice, odkládání pumpy do držáku, bedna s nářadím a další; u pumpy hadice (R) s motorem (B), u výstupu mlýnku hadice
  vleku s přepínačem výstupu. V rámci jedné hadice rozhoduje stav: nesená (vzdálenost 0) > nejbližší možná akce (vzít / odpojit) mezi hadicemi vozidla.
- Nesenou hadici si hráč při nastoupení do vozidla pustí.

## 4. Vzhled, uložení, síť

### Koncovka a spojky
- Koncovka (`_hose_end`, sdt_mlyn.py): zmenšený Storz (měřítko 0,62, vnější Ø ~0,10 m, délka celé koncovky 0,106 m) s objímkou a dvěma sponami, **bez pevné gumové ochrany ohybu** – hadice (Ø 0,064 m) vychází rovnou z objímky.
- Koncovka stojí na čele spojky zdroje, osa po ose, hrana na hranu (bod připojení = čelo uzlu `outlet`). U vody sedí na povrchu karoserie (paprsek) ve výšce 0,3 m nad podlahou, případně u vypouštěcího uzlu.
- Spojky zdrojů (mlýnek, násypka, VSTUP / VÝSTUP pumpy) jsou plný Storz (Ø 0,164 m); objímky: mlýnek červená, násypka žlutá, pumpa modrá / červená. Ventil vleku končí mosaznou zátkou, vstup na koncentrát je kamlok bez Storzu.
- Hadice začíná u spojky vleku / pumpy holým koncem trubky, koncovka je jen na vzdáleném konci.

### Vedení (`SprayDroneHoseLib`)
- Od spojky vychází hadice **rovně ven** (`HOSE_LEAD` 0,30 m, podle potřeby až 1,4 m, aby vyšla z karoserie), u nesené koncovky rovně 0,55 m (`HOSE_HELD_LEAD`); koncovka míří tam, kam hráč hledí.
- Půdorys: nejkratší cesta kolem vozidel (obdélníky `v.size` + odstup 0,4 m, vlastní vozidlo a cíl těsně 0,08 m) a hladká křivka (Catmull-Rom).
- Výška: **leží na zemi** (terén, statický objekt, budova, silnice do 0,6 m nad terénem), k oběma koncům plynule stoupá k výšce spojky; posledních 0,16 m (`HOSE_STIFF`) u koncovky vodorovně ve výšce spojky.
- Hadice nemá volnou délku: kreslí se přesně po vypočtené trase mezi konci, články (72 / 60) se natáhnou.
- Ruka: 0,85 m před kamerou, o 0,25 m níž, nad podlahou, nejdál 0,95 délky od spojky.

### Uložení (savegame)
Ukládá se každá hadice, která je venku, **připojená** a ne nesená: číslo spojky, `uniqueId` zdroje, bod a směr připojení v souřadnicích zdroje, kohout, `targetPort`, příznak rybníka (bod koše světově).
Nesená hadice se neukládá (po načtení je zasunutá). Při načtení se zdroj hledá `RESOLVE_MS` 15 s; nenajde-li se, hadice se tiše zahodí. Připojení nesouhlasící s druhem spojky (např. jiný režim vstupu pumpy) se zahodí.
Režim vstupu pumpy se ukládá jen jako „rybník“. Hladiny nádrží drží FillUnit.

### Síť (MP)
Stav hadic (venku, spojka, kohout, rybník, `targetPort`, nesená poloha, zdroj jako objekt) jde v proudu vozidla; příkazy `CMD_TAKE/DRAG/DROP/CONNECT/VALVE` jdou z klienta eventem (spojka max 15, hadic na vozidlo max 4).
Držitel posílá polohu konce každých 100 ms. Server rozhoduje o toku, utržení a (u rybníka) o hloubce vody.

## 5. Kde to podle kódu nesedí nebo může působit divně

Seřazeno zhruba podle toho, jak moc se to hráči projeví.

1. **Koncovka hadice je menší než spojka zdroje.** Koncovka je Storz v měřítku 0,62 (Ø ~0,10 m, `blender/sdt_mlyn.py:917`), spojky na mlýnku (`sdt_mlyn.py:866`), pumpě (`build_pump.py:217`, `:222`) a násypce (`build_hopper.py:117`)
   jsou plný Storz Ø 0,164 m; napojení čelo na čelo tedy spojuje dva různě velké průměry. Ventil vleku je navíc mosazná zátka (`sdt_bigtank.py:283`) a vstup na koncentrát kamlok bez Storzu (`sdt_tanks.py:841-881`) a na konci hadice
   u spojky vleku / pumpy žádná koncovka není (hadice Ø 0,064 m vychází z Ø 0,164 m spojky pumpy holá).
2. **Délka hadice se nepoužívá při kreslení.** `hoseCurve` přijímá `hoseLength`, ale nikde ho nepoužije (`SprayDroneHoseLib.lua:284`); hadice je vždy přesně tak dlouhá, jak je trasa, nikdy nemá průvěs ani přebytek.
   Utrhne ji až vzdušná vzdálenost (`SprayDroneWaterHose.lua:984`, `:992`), trasa kolem vozidel může být delší než 12 m bez utržení. Komentář v `HoseLib:280-283` („je-li napnutá, zvedá se k přímce“) tomu neodpovídá.
3. **Dosah připojení může přesáhnout délku hadice.** Ruka dosáhne 0,95 délky (`HoseLib:7`, `:441`) a k tomu se přičte dosah hledání: koš do 1,5 m (`WaterHose:46`, `:697`), zdroj 1,1–1,6 m, výstup 2,0 m. Sací hadice pumpy (10 m) tak může
   dostat koš 11 m od pumpy a hned se utrhne (`:992`, „Vodní hadice se utrhla“); u 12m hadice vleku podobně na hraně dosahu.
4. **Dvojí měřítko vzdálenosti vzít / odpojit.** Vzít měří od hráče o 1 m výš (`:1292`), odpojit od hráče bez posunu (`:1275`, `:1282`); u téže spojky tedy jde hadici vzít z místa, odkud ji odpojit nejde (a naopak).
5. **Každý typ zdroje má jiný dosah i jinou metriku:** karoserie 1,1 m vodorovně od obdélníku (`:582`), vypouštěcí uzel 1,6 m 3D (`:559`), vápno 1,5 m 3D (`:550`), ventil vleku 2,0 m 3D (`:645`), nádrž pro výstup 2,0 m vodorovně (`:662`).
   Při porovnávání „nejbližšího“ zdroje se míchají 2D a 3D vzdálenosti (`:550`, `:561`, `:583`), takže vybraný zdroj nemusí být ten nejbližší.
6. **Ventil vleku vždycky přebije bližší cizí nádrž** (`:655-669`): záloha na cisternu se zkouší, jen když v 2,0 m žádný volný ventil není.
7. **Koncovka může sednout na kolo nebo podvozek.** Paprsek zkouší výšky od 0,3 m nahoru a bere první zásah kdekoli na vozidle (`:464-480`, `:514-517`), u cisterny / traktoru tedy často na pneumatiku nebo rám, ne na nádrž.
8. **Texty neodpovídají situaci.** Připojení vápna (i u pumpy) ukazuje „Připojit hadici ke zdroji vody“ (`WaterHose:1264`, `translation_cz.xml:321`); „Odpojit vodní hadici“ (`:330`) i u vápna; `sdt_wh_mixed` říká
   „voda nepoteče“ i u vstupu na vápno (`:950`, `translation_cz.xml:332`); „napustit vodu“ se nabízí, i když vlek žádnou vodu nemá (`:1264`, `:1009`). Řada textů `sdt_mill_hose*`, `sdt_mill_foldHose`, `sdt_mill_noTarget` nemá v kódu žádné použití.
9. **Tiché selhání.** K prázdnému mlýnku / násypce hadice nejde připojit a nikdo neřekne proč (`:547`, `:1265` – hint `tankEmpty` je jen pro vodu); připojená hadice netéče při vypnutém zdroji nebo zavřeném kohoutu bez hlášky (`:1062`);
   „Pumpa nic nečerpá – zapoj hadice“ se ukáže i tehdy, když jsou hadice zapojené a cílová nádrž je plná nebo zdroj prázdný (`SprayDronePump.lua:344-352`); „příliš daleko od uzlu“ u IBC / cisterny s uzlem také bez hlášky (`:559`).
10. **Dvě hadice do jednoho ventilu hlídá jen klient.** Obsazenost se kontroluje při vzetí a hledání cíle (`:1293`, `:642`), server `CMD_CONNECT` bere cokoli, co klient pošle – bez kontroly dosahu, druhu spojky, vody ani obsazenosti (`:847-870`);
    jen rybník server ověřuje (`findPondAt`).
11. **Směr toku rozhoduje stav zdroje v okamžiku připojení.** IBC s 1 l vody je zdroj a nikdy se do něj nenapouští (`:382`); naplněná cisterna se po připojení „napustit“ už nikdy nevypustí zpět (`:1004`). Tentýž ventil vleku
    tak může podle obsahu protější nádrže čerpat i napouštět a hráč to z textu nepozná.
12. **Jednotná osa spojek, ale různé uzly.** Směr, kterým hadice ze spojky vychází, a směr „dovnitř“ se všude bere jako lokální −X uzlu (`:551`, `:646`, `:1129`), ale uzly jsou umístěny různě: u vleku na konci výpusti (`sdt_bigtank.py:269`), u vstupu na koncentrát před
    kamlokem (`sdt_tanks.py:881`), u mlýnku / pumpy / násypky na čele Storzu. Orientaci uzlů jsem v i3d neověřoval – případná chyba se projeví hadicí vedenou do karoserie.
13. **`getDistance` hadicového aktivátoru čte uloženou hodnotu** (`:1363-1365`; bez stavu 0), kdežto pumpslot si ji počítá znovu a výslovně poznamenává, že pořadí volání neznáme (`SprayDronePumpSlots.lua:518`). Pokud hra volá
    `getDistance` před `getIsActivatable`, může nedostupný aktivátor hadice vyhrát. Nesená hadice má navíc vždy vzdálenost 0 (`:1314-1316`) a přebije R akce kdekoli na mapě.
14. **Motor pumpy (B) a hadice (R) soutěží o jeden aktivátor** (`SprayDronePump.lua:425-427` vs `WaterHose:1363`): vedle pumpy se podle vzdálenosti nabídne jen jedno z nich, takže motor jde spustit, jen když stojíš blíž k motoru než ke spojce.
15. **Trasa může vést skrz vozidlo.** Při neúspěchu hledání cesty vrací `routeAround` prázdnou trasu = přímka (`HoseLib:226-228`); překážkami jsou jen vozidla s výškou ≥ 0,4 m (`:73`) a podlahu netvoří dynamické objekty (`:16`),
    takže hadice přes IBC či paletu nezvedne ani neobejde.
16. **Rybník: první nalezený bod, ne nejbližší ani nejhlubší** (`WaterHose:697-705`) – podle pořadí směrů v kruhu. Odpojení u koše (`UNPLUG_DISTANCE` 2 m od bodu pod hladinou) vyžaduje stát u břehu; jinak jen u pumpy.
17. **Skládání vleku s hadicí venku nic nehlídá** (`SprayDroneStation.lua` nemá žádný odkaz na hadice; text `sdt_mill_foldHose` je nepoužitý), hadice zůstane připojená a ve 12 m se utrhne.
18. **Zastaralá dokumentace a mrtvé konstanty.** `docs/DRON.md:1553` píše výstup „do 1,0 m“ (kód 2,0 m), `:2045` „~0,26 m `HOSE_STIFF`“ (kód 0,16); `HOSE_EXTRA_SHARE` / `HOSE_EXTRA_FIXED` (`HoseLib:8-9`) se nepoužívají.
