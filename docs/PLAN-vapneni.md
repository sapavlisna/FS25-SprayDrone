> **Stav 2026-10-18:** kroky 0–5 jsou naimplementované a offline ověřené (`tools/check_all.py --no-build`: validate_mod, check_xml_nodes, check_compound, lua_check,
> audit_spec_fields, test_mixer, ...), **ve hře nic neověřeno**. Popis hotové věci je v `docs/DRON.md` (sekce „Vápnění“). Odchylky od plánu: pohon mlýnku je vlastní nafta
> (fill unit 2 vozíku), Max má vápennou konfiguraci jako dvě nové `fillUnitConfiguration` (3 000 / 5 000 l) a vždy zadní kulový věšák (vehicleType `sprayDroneTrailerTow`),
> vozík se zapřahá za Max nebo za jiný tahač a hadice ho s nádobkou spojuje bez zapřažení (dosah 9,5 m). Pytle a pytlování zůstávají na další fázi.

# Plán: vápnění dronem — mlýnkový vozík s hadicí a vápenná varianta Maxu (FS25-SprayDrone)

## Context

Pavel chce, aby dron uměl vápnit pole. Jemně mleté vápno se nasype do nádobky u mixéru a mixér při plnění dronu z něj s vodou udělá kapalinu
k vápnění; počítá se s obrovskou spotřebou. Zdroj jemného vápna bude **samostatný malý vozík**: sedí na něm **nádoba na hrubé vápno** a **mlýnek**.
Vozík se připojí **hadicí k Maxu** (do nádobky u mixéru, hráč hadici viditelně spojí), později případně k pytlování (pytle jemného vápna).
Max má při **konfiguraci na vápno zvětšenou nádobku u mixéru** (fill unit 3), plnitelnou hadicí (a později z pytlů). Nádrž B a sání zůstávají beze změny.

**Rozsah tohoto plánu:** (A) jádro vápnění, (B) vápenná konfigurace Maxu, (C) mlýnkový vozík s jednoduchým, ale úplným modelem a Lua logikou,
(D) viditelná hadice vozík→Max. **Mimo rozsah (až potom, bude to snazší):** pytle/pytlování, Mini/Middle, plnění z ruky/kanystrů s vápnem, ladění spotřeby, Precision Farming.
**Vývoj jde v nové větvi** (krok 0). **Pořadí práce (Pavel):** nejdřív modely k souhlasu (krok 1), teprve potom Lua/XML a hadice.

Průzkum (4 agenti, klíčová místa ověřena proti zdrojům): dron + mixér už umí vše potřebné — koncentrát + voda → produkt, který dron nese, a zápis na pole přes
`FSDensityMapUtil.updateSprayArea`. Vápno je jen **další koncentrát + produkt s vanilla sprayType LIME**; zbytek práce je vozík, hadice a model Maxu.

## Zjištěná fakta

- **Tok dnes:** fill unit 3 (koncentrát) + voda z fill unit 1 → `SprayDroneMixer.resolve` → `pumpDrone` míchá při plnění dronu → `spec.droneFillType` = vanilla produkt →
  `flushSpray` → `updateSprayArea` (`SprayDroneStation.lua:1808, 1851, 1881, 2781, 2811, 3404`).
- **Produkt = vanilla `LIME`:** `getSprayType` bere `g_sprayTypeManager:getSprayTypeByFillTypeIndex`; vanilla sprayType LIME (`maps_sprayTypes.xml:9`, `litersPerSecond 0.09`, `isLime`)
  funguje bez registrace; hlavní nádrž produkt mít nemusí (`spec.droneFillType` se nastavuje přímo).
- **Spotřeba:** `lps × 36 000 × usageScale (0,2)` = **648 l/ha** (hnojivo 58). Dávka dronu S/M/L (20/40/75 l) pokryje 0,03 / 0,06 / 0,12 ha.
- **Ve hře:** `LIME_LEVEL` (0–3), jen při savegame nastavení `limeRequired`; zapíše se **jen na holou půdu / strniště / čerstvě zasetou / přerostlou plodinu**, na rostoucí ne;
  zakázky na vápnění nejsou (`getFieldAllowed` `:2306` zakázku s vápnem odmítne správně).
- **Max:** `fillUnitConfiguration` „2 × 3000 l“ (`TANK6000`) / „2 × 5000 l“ (`TANK10000`) v `blender/templates/sprayDroneTrailerMax.xml.in:198-240`; fill unit 3 = koncentrát 300/500 l
  s `exactFillRootNode` = `concentrateFillRootNode`; mixér/čerpadlo/indukční nádobka v mezeře mezi nádržemi (y 1,80–3,14; indukční x −0,78…−0,32, čerpadlo a mixér u pravé strany).
- **Compound limit** (`tools/check_compound.py`): Max 39/40; tvary přepínané konfigurací se počítají jen v nejhorší aktivní konfiguraci. Zvětšená nádobka nesmí přidat kolizní kvádr
  navíc: buď se sdílí existující `colInduction*` (větší obálka), nebo se ověří, že součet zůstane ≤ 40.
- **Hadice dnes:** jen vizuální řetěz vlek→dron: články `fillHoseSeg1..96` v i3d vozidla, `layoutHose(hose, hoseT)` a `getHangingLine` (prověšená Bézierova křivka) v `SprayDroneService.lua:531-713`;
  cíl je jen `<prefix>FillPort` na témže vozidle; sync `hoseT` přes `SprayDroneFields.lua:47`; zvuky `hoseAttach/hoseDetach` jsou vanilla šablony. Obecný systém hadice mezi dvěma vozidly není.
- **Přečerpání dnes** (`SprayDroneService.lua:717-867`): skriptové, server po tikách (`addFillUnitFillLevel` ± množství), čerpadlo potřebuje centrálu; `SprayDroneServiceEvent` `NUM_BITS=2` (plné).
- **Vozidla v modu:** typ `sprayDroneTrailer` (parent `baseFillable` = fillUnit, fillVolume, cover, attachable) pro vleky; `sdtRelayPole` (pallet). Registrace v `modDesc.xml` (`<specializations>`, `<vehicleTypes>`, `<storeItems>`).
- **Blender pipeline:** `Mesh` v `sdt_tanks.py`, vzor stroje `sdt_mixer.py`, oj a kola v `build_trailer_mini.py` (`build_drawbar`, kola), exportér `export_mini_mod.py`, `headless_*.py -- build export`, kontroly `tools/check_all.py`.

## Rozhodnutí (default; jde změnit konstantou)

1. **Produkt vanilla `LIME`**, jemné vápno = nový fillType **`SDT_FINE_LIME`** („Jemně mleté vápno“, sypký, ~1,1 kg/l), `<ratio fillType="SDT_FINE_LIME" product="lime" concentrate="0.20"/>`.
   Spotřeba vanilla × `usageScale` (648 l/ha, „spousta“).
2. **Max, vápenná konfigurace** (nová `fillUnitConfiguration` `TANK6000_LIME` / `TANK10000_LIME` s příplatkem): fill unit 3 se zvětší (cíl 600 / 1000 l, přesně podle toho, co se vejde do
   mezery; stávající 300 / 500 l), visí na něm větší model nádobky (`objectChange` mezi `induction…` a `inductionLime…`), přibude hadicová spojka (`limeInletPort`) a štítek.
   Typy ve fill unit 3 zůstanou všechny tři (`SDT_FINE_LIME` + dva stávající koncentráty), jednotka drží vždy jen jeden druh.
3. **Mlýnkový vozík** = nový vozidlový typ `sdtLimeMill` (parent `baseFillable`, vlastní specializace `sprayDroneMill`): malý odpojitelný vlek (oj + jockey + jedna náprava, vzor Mini),
   - **fill unit 1: hrubé vápno** (vanilla `LIME`, nádoba cca 1500 l, `exactFillRootNode`: vyklopí se do ní vanilla návěs / big bag),
   - **fill unit 2: nafta** (motor mlýnku, 30 l; nalévání stejným způsobem jako u centrály Maxu),
   - **fill unit 3: jemné vápno** (`SDT_FINE_LIME`, malý mezisklad ~200 l, ze kterého jde hadice),
   - skript: hráč motor zapne/vypne akcí (vzor `SprayDroneToolboxActivatable`), za běhu mele `LIME → SDT_FINE_LIME` rychlostí `millRate` l/s a spotřebuje naftu; mele jen když je kam dát výstup
     (mezisklad volný nebo hadice připojená).
4. **Hadice**: hráč u vozíku akcí „připojit hadici“ spojí `millHoseNozzle` vozíku s `limeInletPort` nejbližšího Maxu v dosahu (délka hadice cca 8 m); hadice se vykreslí mezi nimi
   (znovupoužití `getHangingLine`/`layoutHose`: vozík vlastní články, koncový bod je světová poloha portu Maxu přepočtená do lokálních souřadnic vozíku); při pohybu/vzdálení nad dosah se sama
   odpojí; po připojení čerpadlo vozíku (běží s motorem) přesouvá `SDT_FINE_LIME` z jemného meziskladu do fill unit 3 Maxu (`addFillUnitFillLevel`, zabránit nesouladu druhu v nádobce — jako `Toolbox.getTankReason`).
   Stav (připojeno, cíl) se ukládá a synchronizuje po síti (dirty flag + vlastní event podle `SprayDroneRelayEvent`).
5. **Pytlování a pytle jemného vápna** jsou až další fáze; vstup do fill unit 3 Maxu zůstane stejný (`addFillUnitFillLevel`), takže pytle se napojí později bez přestavby.

## Kroky

### 0. Větev a dokumentace
- V `E:\ClaudeProjects\FS25-SprayDrone`: `git switch -c feature/vapneni` z `main` (obsahuje commit galerie `fddf197`). Necommitované `__pycache__`/`out/` změny nechat být.
- Plán zkopírovat do `docs/PLAN-vapneni.md` (soubory jen v projektu). Commity až na Pavlovu žádost.

### 1. MODELY K SOUHLASU (nejdřív, stop před zbytkem)
Pavel chce **nejdřív vidět modely**. Proto se po kroku 0 dělají jen Blender modely a jejich náhledy; **žádná Lua, žádné XML, žádný export do modu, žádná hra**, dokud Pavel modely neschválí.
- **Mlýnkový vozík** (`blender/sdt_mlyn.py`, `blender/build_trailer_mill.py`, `headless_mill.py -- build render`): malý jednonápravový vlek s ojí, nádobou na hrubé vápno (horní otvor), mlecí skříní, motorem s palivovou
  nádrží, výsypkou do jemného meziskladu a hadicovou spojkou. Jednoduchý, čistě tvarově čitelný model ve stylu stávajících vleků (materiály z `MATERIALS`, barvy a polepy jako Mini). Hrubé rozměry: ~2,6 × 1,5 × 1,8 m.
- **Max, vápenná varianta nádobky u mixéru** (`build_trailer_max.py`, varianta `inductionLime`): větší nádobka na místě indukční, s hrdlem, štítkem „JEMNÉ VÁPNO“ a spojkou `limeInletPort` pro hadici;
  vejde se do mezery mezi nádržemi (kontrola na renderu proti čerpadlu, mixéru a výtlaku).
- **Koncept hadice**: náhled mlýnkového vozíku vedle Maxu s hadicí nataženou ze spojky vozíku do spojky Maxu (jen v Blenderu, orientačně kvůli délce a výšce spojek).
- **Výstup:** sada PNG náhledů (pohledy zepředu, zezadu, z boku, shora, detail spojek, vozík vedle Maxu) do `tmp/vapneni/modely/` v projektu a jejich ukázka Pavlovi; změny podle jeho připomínek.
  Kroky 2–6 začnou až po jeho souhlasu s modely.

### 2. Jádro vápnění (Lua/XML)
- `xml/fillTypes.xml`: `SDT_FINE_LIME` (sypký, ikona `hud/fillTypes/hud_fill_sdtFineLime.dds` z `tools/png2dds.py`, překlady `fillType_sdtFineLime` v `translation_{cz,en,de}.xml`).
- `SprayDroneStation.lua:1825` záložní seznam koncentrát→produkt doplnit o vápno (Max má vlastní `<mixer>`).
- Plánovač: informativní řádek, že vápno se na rostoucí plodinu nezapíše (podle stavu pole), žádná další logika.
- `tools/test_mixer.py` (voda + `SDT_FINE_LIME` → `LIME`, omezení), `tools/prepare_testsave.py` (`--concentrate-type lime`), `SprayDroneDebug.lua` (`fillConcentrate -ConcentrateType lime`).

### 3. Max: vápenná konfigurace s větší nádobkou (napojení schváleného modelu)
- Z kroku 1 převzít schválenou nádobku `inductionLime…`, štítek (`decal_layout.REGIONS`, `tools/make_decal_atlas.py`, `sdt_labels.py`), spojku `limeInletPort`, kolizi sdílenou/zvětšenou;
  hrdlo `concentrateFillRootNode` přesunout k větší nádobce.
- `sprayDroneTrailerMax.xml.in`: dvě nové `fillUnitConfiguration` podle vzoru ř.203-239, nové uzly do `MAPPED_NODES` (`export_max_mod.py` ř.23) nebo `sdt_mapped=1`, `<ratio fillType="SDT_FINE_LIME" product="lime" concentrate="0.20"/>`
  do `<mixer>` (ř.378-381), překlady názvů konfigurací.
- Re-export `blender.exe -b --python blender\headless_max.py -- build export` (~20 min), `tools/check_all.py --only max`, `check_compound.py` (≤ 40), `check_xml_nodes.py`, `validate_mod.py`; `-- build render` pro vizuální kontrolu.

### 4. Mlýnkový vozík: export, typ, Lua
- **Blender:** schválený model z kroku 1 doplnit o funkční uzly (`exactFillRootNode` kvádr nad nádobou, hrdlo nafty, `millHoseNozzle`, články hadice `millHoseSeg1..N`, `mlynMotor`, `mlynSoundNode`), kolize `compoundChild`
  (density 0.001) pod `collisions`, `export_mill_mod.py` (vzor `export_mini_mod.py`), obrázek do obchodu (`_fit_camera`).
- **Mod:** `blender/templates/sdtLimeMill.xml.in` → `vehicles/sdtLimeMill/sdtLimeMill.xml`, `modDesc.xml` (`<specializations>` `sprayDroneMill`, `<vehicleTypes>` `sdtLimeMill`, `<storeItems>`, překlady cz/en/de), `scripts/SprayDroneMill.lua`
  (načíst v `modDesc` `extraSourceFiles`/`<specializations>`; funkce: akce motor start/stop, mletí po tikách na serveru, spotřeba nafty, vazba na `<mill rate millRate dieselPerHour hoseLength/>` v XML, ukládání do savegame, `writeStream/readStream` stavu).
- Zvuky: vanilla vzorky přes `$data` (motor, mlýn).

### 5. Hadice mlýnek → Max
- `scripts/SprayDroneMill.lua`: hledání nejbližšího Maxu s `limeInletPort` v dosahu (`g_currentMission.vehicleSystem.vehicles` jako `getTransferPallet`), akce spojit/odpojit (ACTIVATE_OBJECT u `millHoseNozzle`),
  kontrola dosahu (jako `SprayDronePad.hoseReaches`), odpojení při překročení délky nebo při zrušení motoru, přesun `SDT_FINE_LIME` do fill unit 3 Maxu s kontrolou druhu a volné kapacity.
- Vizuál: zobecnit `layoutHose`/`getHangingLine` (`SprayDroneService.lua:531-713`) tak, aby koncový bod mohl být cizí uzel (nová funkce, stávající beze změny); sync stavu hadice (`SprayDroneFields`-styl pole + event `SprayDroneMillEvent`
  podle `SprayDroneRelayEvent`); `hoseAttach/hoseDetach` zvuky jako dnes.
- Max na straně vleku nic dalšího neřeší: dostává litry do fill unit 3 vanilla voláním, mixér pak míchá beze změny.

### 6. Ověření (hra jen s Pavlovým souhlasem)
- Offline: `test_mixer.py`, `lua_check.py`, `audit_spec_fields.py`, `validate_mod.py`, `check_xml_nodes.py`, `check_compound.py`, `check_all.py`; nový offline test mlýnku (aritmetika mletí a přesunu) podle `test_mixer.py`.
- Hra (`tools/sdt_start.ps1`, `sdt_debug.ps1`, po testu `-Stop`; savegame s `limeRequired`, holé pole): S1 produkt LIME zvedne `LIME_LEVEL` a spotřeba ≈ 648 l/ha; S2 návěs vyklopí do nádoby mlýnku,
  motor běží a mele; S3 hadice se spojí, nádobka Maxu se plní; S4 celý řetěz voda + prášek → dron → pole. Zjištění z testů rozhodne o pytlích a dalších krocích.

### 7. Plnění big bagu z mlýnku a výsypná stolice násypky (2026-10-29, hotovo mimo hru)
- Podle `docs/NAVRH-mlyn-plneni-bigbagu.md` (schváleno): ventil (rozdělovač) s pákou na výstupu (Y / klik na páku; jde i s připojenou hadicí, ta pak nic nedostane), výsypná roura
  s otočným kloubem v pravém zadním rohu a plnicí hlavou 1,32 m nad zemí nad „ramenem“ vaku, tři polohy (O: přeprava -> vedle -> za -> přeprava, pěšky klik na kloub; vlastní
  animace `spoutSwing`, ne vanilla `Pipe`), vak se hledá / staví pod hlavou; `fillPlane` hrubého vápna. Foukací roura `blowPipe.i3d` zrušena (`blender/archiv/build_blowpipe.py`).
- Násypka: nástavec a výsypná stolice (vak se jen položí, sype vanilla rychlostí), zásoba 400 l, `fillPlane`, vysouvací opěry (vak sype jen s vysunutými), plnění bez motoru.
- Offline: `tools/test_mill_flow.py` (v `check_all`), náhledy exportu `out/mill_build_check/`. Ve hře neověřeno, popis a příkazy v `docs/DRON.md` („Big bag z mlýnku“, „Násypka“).

## Otevřené body

- **Pohon mlýnku:** default vlastní nafta + akce motoru. Alternativa PTO z traktoru (vanilla `powerConsumer`) je jednodušší, ale vozík by nešel pohánět za pickupem; rozhodnout při kroku 3.
- **Hadice mezi dvěma vozidly** je největší riziko (nový sync, odpojení při jízdě, přilepení k tahači). Nejdřív prototyp vizuálu `layoutHose` s cizím koncem a až potom logika přesunu.
- Kapacita zvětšené nádobky a její tvar se rozhodne podle renderu (vejde se mezi nádrže/hadice?). Těžiště Maxu: vápno 1,1 kg/l × 1000 l = 1,1 t, ověřit náklon.
- Podíl 0,20 a spotřeba 648 l/ha jsou odhad; po S1/S4 doladit.
- `harvestScaleRation` (výnosový bonus za vápno) není ve zdrojích; ověřit nepřímo ve hře. Precision Farming větve (`SprayDroneStation.lua:2079-2166`) jsou neověřené.

## Kritické soubory

`blender/templates/sprayDroneTrailerMax.xml.in`, `blender/build_trailer_max.py`, `blender/export_max_mod.py`, `blender/decal_layout.py`, `blender/sdt_labels.py`, `tools/make_decal_atlas.py`,
`mod/FS25_SprayDroneTrailer/xml/fillTypes.xml`, `scripts/SprayDroneStation.lua`, `scripts/SprayDroneService.lua`, `modDesc.xml`, `translations/translation_{cz,en,de}.xml`;
nové `blender/sdt_mlyn.py`, `build_trailer_mill.py`, `headless_mill.py`, `export_mill_mod.py`, `blender/templates/sdtLimeMill.xml.in`, `scripts/SprayDroneMill.lua`, `scripts/events/SprayDroneMillEvent.lua`;
`tools/test_mixer.py`, `tools/prepare_testsave.py`, `tools/make_release.py` (nové `.py` do `BLENDER_SCRIPTS`/`TOOLS`), `docs/DRON.md`.
Znovupoužít: `SprayDroneMixer.resolve`, `layoutHose`/`getHangingLine`, `SprayDroneService.getTransferPallet` (vzor hledání cíle), `Toolbox.getTankReason`, `SprayDroneRelay.lua` + `SprayDroneRelayEvent` (vzor stavu a eventu),
`SprayDroneToolboxActivatable` (vzor aktivace), `export_mini_mod.py` a `build_trailer_mini.py` (oj, kola, exportér).

## Pravidla z projektu

Vanilla mechaniky místo vlastních náhražek; plán/dokumenty ověřovat proti kódu; soubory jen v projektu; commit/push jen na žádost; nepouštět hru bez pokynu; kolizní kvádry `compoundChild`;
v Lua nepoužívat `goto continue`; Blender 5.1.2 (`SDT_BLENDER` v `local_paths.json`), export Maxu ~20 min.
