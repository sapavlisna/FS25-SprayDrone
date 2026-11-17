# Díly zvlášť v Blenderu, vlek se z nich skládá (2026-10-23)

Pavel schválil „úroveň 1“: každý díl má vlastní stavbu a `.blend`, sestavení vleku si díly připojí a výsledkem
zůstává jeden i3d (v módu se nic nemění). Tady je měření současné pipeline, prototyp na centrále a návrh zavedení.

## 1. Měření (Middle, headless, priorita BelowNormal, Pavel na PC pracoval)

Skripty: `tmp/parts_proto/measure_middle.py` (obal kolem `build_trailer_middle.build()` a kroků
`export_middle_mod.build_mod()`, všechny výstupy přesměrované do `tmp/parts_proto/out_<tag>`, mód ani
`spraydrone_trailer_middle.blend` se nemění), spouštění `tmp/parts_proto/run_blender.ps1`.

| krok | čas | poznámka |
|---|---|---|
| stavba scény (`build`) | 11–13 s | 1 269 objektů; z toho centrála < 1 s |
| uložení .blend | 0,1 s | |
| bake vmask (`bake_vmasks`) | 128–135 s | **na CPU** – GPU jsem vypnul (`CUDA_VISIBLE_DEVICES=-1`), protože ho vytěžoval jiný proces; běžně jede OPTIX a bude rychlejší |
| export i3d (`export_i3d`) | 36 s | 1 567 uzlů, 1 283 shapes; s profilerem 65 s |
| shader, skrytí uzlů, i3dMappings, XML | < 0,2 s | 656 mappingů |
| obrázek do obchodu a ikona | – | bez okna se nekreslí (vynecháno i v měření) |
| **celkem** | **≈ 3,5 min** (bez bake 48 s) | |

Max jsem neměřil; má zhruba dvojnásobek meshů (dva drony, dvě centrály), čekám zhruba dvojnásobný export i bake.

**Kde se tráví čas exportu** (cProfile, `tmp/parts_proto/profile_middle*.txt`): skoro celý export je zpracování meshů
po jednom – `dccBlender.getShapeData` (1 283×) 43 s z 65 s s profilerem, z toho `i3d_densityUtil.computeUvDensity`
17 s (výpočet hustoty UV pro streamování textur, nejde vypnout – je to výstupní údaj); serializace XML ~6 s; převod
`.shapes` externím procesem ~3 s. Export tedy roste s počtem meshů a knihovna dílů ho **nezrychlí** – vlek je pořád
jeden i3d se všemi meshi.

## 2. Prototyp: centrála z knihovny dílů

Soubory:
- `blender/parts_lib.py` – knihovna: `PARTS` (díl → zdrojové `.py` pro klíč cache), `part_key` (SHA1 zdrojů + parametrů
  JSON), `ensure_part` (chybí-li `blender/parts/<díl>_<klíč>.blend`, postaví ho v **samostatném procesu Blenderu**,
  `--factory-startup`, scéna s jedinými objekty dílu a body ve vlastnosti scény), `place_part` (append scény, přesun
  objektů do kolekce vleku pod `_root`, přemapování materiálů podle jména na `sdt_parts.material`, úklid sirotků),
  `build_generator` (náhrada `sdt_generator.build_generator` se stejným rozhraním a návratovou hodnotou),
  `preview` (náhled dílu Cycles na CPU, 640 px, ~3 s).
- Zapojení v prototypu bez změny skriptů vleku: `measure_middle.py --parts` nastaví
  `car["G"].build_generator = parts_lib.build_generator` po načtení `build_trailer_middle.py` a před `build()`.
- Náhled: `out/parts/generator.png`.

Časy: stavba dílu v novém procesu 0,7–0,9 s (včetně startu Blenderu), připojení z cache 0,01 s, stavba celého
Middle s dílem z cache stejná jako bez knihovny (11–12 s).

### Rovnocennost exportu – ověřeno

Porovnání `tmp/parts_proto/compare_i3d.py` (i3d, `.shapes`, XML vleku) a `diff_meshes.py` (každý mesh scény: poloha
vrcholů, všechny atributy, obě UV, materiály, vlastnosti `i3D_*`, matice):
- všech 1 269 objektů scény shodných, **včetně DirtUV** (0 rozdílů; dvě stavby bez knihovny jsou taky 0 rozdílů –
  pipeline je deterministická),
- i3d: 1 567 uzlů ve stejném pořadí, žádný uzel s jinými atributy, 52 shodných materiálů, 48 souborů,
- XML vleku (i3dMappings, díly) bajtově shodné,
- `.shapes` stejná velikost (25 644 948 B); bajtově se liší i dva exporty bez knihovny (soubor je kódovaný
  s náhodným semínkem v hlavičce), takže bajtové srovnání nic neříká.

### Co se cestou ukázalo (pravidla pro další díly)

1. **Díl se musí stavět na svém místě, ne v počátku a pak posunout.** `sdt_parts._box_uv` počítá UV kvádrů ze světových
   souřadnic a posun mění zaokrouhlení float32 vrcholů. Obojí změnilo UV0 rámu a pak přes společné balení DirtUV
   všech 1 031 meshů vleku. Poloha je proto součástí klíče cache (díl se přestaví, když se posune).
2. **Parametry předávat v původním typu.** Zásuvka převedená přes `Vector` (float32) posunula 16 vrcholů o 1 ulp a to
   stačilo na jiné balení DirtUV pro 8 meshů. Tuple doublů v JSON je bezztrátový.
3. **Prázdné uzly po appendu:** `matrix_world` načteného objektu je neaktuální (identita) – nastavovat `matrix_basis`.
4. **Balení DirtUV je globální** (smart project + pack přes všechny meshe vleku naráz) a citlivé na jakoukoli změnu
   geometrie. Změna dílu tedy vždy znamená nové DirtUV celého vleku a nový bake vmask – to knihovna neodstraní.

## 3. Kolik to ušetří

- **Úprava jednoho dílu:** stavba dílu ~1 s + náhled ~3 s, místo stavby a kontrolních renderů celého vleku
  (`headless_middle.py -- build render` ≈ 12 s stavba + EEVEE pohledy) nebo plného exportu (~3,5 min Middle). Hlavní
  přínos: díl se ladí a kontroluje samostatně, jiný díl ani vlek se při tom nepřestavují.
- **Plný export vleku:** úspora prakticky žádná (stavba 12 s je zanedbatelná proti bake a exportu). Plný export by
  zrychlilo jen:
  - cache bake vmask – přeskočit `bake_vmasks`, když se nezměnila geometrie ani DirtUV (hash meshů; dnes ruční
    `--no-bake`), úspora 2 min (CPU) na Middle,
  - bake na GPU (běžný stav, když GPU nevytěžuje jiný proces).

## 4. Návrh zavedení pro všechny díly

Díl = čistá funkce parametrů (poloha, varianta, zrcadlení…) vracející objekty a body. Pořadí:

1. **Centrála** (`sdt_generator`) – hotový prototyp. Zavést přímo ve `build_trailer_middle.py`, `_max.py`
   (dvě centrály, druhá zrcadlená, `rear_socket`), `_mini.py` (po stavbě se otáčí – otočení zůstane v sestavení, díl se
   staví neotočený, jak to dělá dnes).
2. **Statické vybavení**: indukční nádrž a čerpadlo (`sdt_tanks`), mixér (`sdt_mixer`), mlýnek (`sdt_mlyn`), hlavní nádrže
   (`sdt_bigtank` – víc variant objemu v jednom dílu, viditelnost řeší konfigurace), ráfky (`sdt_rims`, už mají vlastní
   export). Nízké riziko, stejný vzor.
3. **Drony** (`build_drone`) – největší přínos pro opakované použití (Mini/Middle/Max, tři varianty, a hlavně
   **složený dron jako předmět** z `NAVRH-dron-predmet.md` – jeden díl pro vlek i předmět). Vyšší riziko: uzly skládání,
   listy, kamery a světla jsou v i3dMappings a v `foldPart`/`navLight` v XML; `place_drone` je umisťuje podle vleku
   (díl by se stavěl na místě plošiny, viz pravidlo 1).
4. Specifické díly vleku (skříň na kanystry, žebřík, plachty, rám) **nechat ve skriptu vleku** – jsou jednorázové
   a provázané s konstrukcí.

Rizika a opatření:
- **Klíč cache** je dnes ruční seznam souborů v `PARTS`; zapomenutý pomocný modul = zastaralý díl. Lepší: při stavbě
  v podprocesu zapsat seznam skutečně načtených modulů z `blender/` (rozdíl `sys.modules`) do `.json` vedle `.blend`
  a klíč počítat z něj.
- **Sdílené materiály**: přemapování podle jména na `sdt_parts.material` (ověřeno, žádné `.001`). Materiály dronu `__D`
  vznikají až v `build_dirt_uvs` – beze změny.
- **Jména uzlů** vázaná na XML a Lua zůstávají (append nemění jména, když ve scéně nejsou); i3dMappings se počítají po
  exportu podle jmen – ověřeno.
- **Stav modulů**: díl nesmí spoléhat na globální stav modulu, který čte zbytek vleku (např. `sdt_generator._O`);
  vše potřebné vrací v bodech dílu.
- **Vmask a decaly**: DirtUV a bake zůstávají po sestavení nad celým vlekem (pravidlo 4), atlas nálepek beze změny.
- **Cache na disku**: `blender/parts/` přidat do `.gitignore` (dnes tam není).

## 5. dynamicallyLoadedParts (díly jako samostatné i3d ve hře) – nedoporučuji

- Uzly v takovém dílu nejsou v i3dMappings vleku – nejde na ně XML (animace, kolize, plnicí uzly, efekty výfuku).
- Vmask je jeden atlas na vlek; samostatný i3d by potřeboval vlastní vmask a vlastní bake.
- Úspora exportu je úměrná počtu meshů dílu – centrála má 5 z 1 283, tedy zanedbatelná.
- Načítá se asynchronně (`loadSubSharedI3DFile`), Lua by uzly hledala až po načtení.

Smysl by mělo jen pro velký statický díl sdílený mnoha vozidly; takový v módu není. Složený dron jako předmět bude
stejně samostatný i3d (vlastní objekt), na to dynamicallyLoadedParts potřeba není.

## 6. Zavedení do vleků (2026-10-23)

Knihovna je zapojená přímo ve skriptech vleků; příkazy stavby a exportu se nemění (`headless_middle.py`, `headless_max.py`,
`headless_mini.py`, `export_*_mod.py`). Cache je v `blender/parts/` (v `.gitignore`).

### Jak to funguje

- Volání dílu ve skriptu vleku: `PL.call(G.build_generator, at=PL.Place.at(x, y, z))` (díl se staví v lokálním počátku, viz sekce 7).
  Funkce se zavolá v samostatném Blenderu (`--factory-startup`), díl se uloží do
  `blender/parts/<modul>.<funkce>_<otisk parametrů>.blend` + `.json` (výsledek funkce, pořadí objektů v kolekci, objekty pod
  kořenem, zdroje a konstanty). Připojení vrací totéž co přímé volání (Vector, tuple, dict, objekty podle jména).
- **Závislosti automaticky**: moduly z `blender/`, které modul dílu importuje (i nepřímo, statický rozbor importů) –
  sha1 jejich zdrojů a `parts_lib.py` je v `.json`; změna kteréhokoli = přestavba dílu.
- **Konstanty modulů**: Max a Mini za běhu přepisují konstanty modulů nádrží (`T.PUMP_XY`, `T.INDUCTION_XY`, `BT.MAIN_DRAIN`,
  `decal_layout.TANK_GEOM`…). Hodnoty všech přenositelných konstant závislých modulů v okamžiku volání jdou do podprocesu
  (nastaví se po importu) a do platnosti cache. Když sestavení v závislém modulu nahradí **funkci** (jiný soubor/řádek než
  ve zdroji), díl se postaví přímo ve vleku (`přímo` ve statistice) – dnes se to neděje.
- **Parametry bezztrátově**: Vector/Matrix/tuple/dict (i číselné klíče) se přenášejí jako double, takže nevzniká posun
  float32 z prototypu.
- Po připojení se volá `view_layer.update()` (jinak má empty z knihovny neaktuální `matrix_world` a `P.group` ho zařadí
  špatně – na Maxu se tím rozjela poloha `generatorExhaust2`, opraveno).
- `SDT_PARTS=0` knihovnu vypne (všechno se staví přímo, výsledek je stejný).
- Náhled dílu: `blender.exe -b --factory-startup --python blender\parts_lib.py -- preview <díl>.blend <png>`
  (Cycles CPU, ~11 s včetně startu Blenderu), např. `out/parts/generator.png`.

### Které díly

| díl | Middle | Max | Mini |
|---|---|---|---|
| centrála `sdt_generator.build_generator` | 1 | 2 (druhá zrcadlově umístěná) | 1 (umístěná otočená) |
| indukční nádrž `sdt_tanks.build_induction_tank` | ✓ | ✓ | ✓ |
| čerpadlo `sdt_tanks.build_pump` | ✓ | ✓ | ✓ |
| hlavní nádrže `sdt_bigtank.build_main_tanks` | ✓ | – (Max staví vlastní dvě nádrže z dílčích funkcí BT, vázané na rám) | – (hranatá nádrž z dílčích funkcí) |
| vápenná nádobka a tažný věšák `sdt_lime` | – | ✓ | – |
| mixér `sdt_mixer.build_mixer` | – | – (čerpadlo s mixérem je v rozvodu) | ✓ |
| pneu a disky `sdt_rims.build_tire` / `build_rim` | ✓ | ✓ (disky) | ✓ (kód Middle) |

Mimo knihovnu zůstaly: rozvody a hadice (`build_plumbing*`, Max ho za běhu přepisuje hákem), nádrže Maxu a Mini (sestavené
z dílčích funkcí `BT._shell/_manway/…` přímo v rámu vleku), skříň na kanystry, žebřík, plachty, rám, navíječe, nálepky –
jednorázové a provázané s konstrukcí vleku. **Mlýnek** (`sdt_mlyn`) je samostatné vozidlo `build_trailer_mill.py`, ve vlecích se
z něj používá jen pomocná funkce koncovky hadice – do knihovny nepatří. **Drony** zatím ne (viz níže).

### Cache vmask (bake)

`export_middle_mod.bake_vmasks` (platí i pro Max a Mini) spočítá otisk všeho, na čem vmask závisí – meshe průchodů (matice,
vrcholy, rohové normály, DirtUV, materiály ploch), parametry materiálů a zdroj exportu – a když v `blender/parts/bake/` leží
`<atlas>_<otisk>.dds/.png`, jen je zkopíruje (otisk 0,1–0,4 s). Jinak peče a výsledek uloží. Vynucení: `SDT_FORCE_BAKE=1` nebo
`--force-bake`; `--no-bake` funguje dál. Pečení je deterministické (čerstvý bake Mini a dronů je bajtově shodný s módem).

### Rovnocennost (tmp/parts: `build_export.py`, `compare_digest.py`, `compare_export.py`)

Pro každý vlek: stavba bez knihovny (`SDT_PARTS=0`) a s knihovnou (studená i teplá cache), export do `tmp/parts/out_*`:
- **scéna**: všechny objekty (Middle 1 575, Max 2 356, Mini 845) shodné – vrcholy, UV včetně DirtUV, atributy, matice,
  vlastnosti, kolekce včetně pořadí objektů, materiály,
- **export proti módu** (`mod/…/<vlek>.i3d`, `.xml`): uzly ve stejném pořadí se stejnými atributy, materiály s texturami,
  soubory, XML vleku shodné; `.shapes` stejná velikost (obsah plyne ze shodné scény, bajtově ho porovnat nejde – náhodné
  semínko v hlavičce).

Do `mod/` jsem nic neexportoval: i3d a XML by vyšly stejné a `.shapes` by se změnil jen semínkem. **Zjištění**: vmask vleku
v módu u **Middle a Max neodpovídá současné geometrii** (čerstvý bake se liší ve ~20 % pixelů; Middle vmask je z commitu
`aafe830` 15. 10., `.shapes` z 22. 10. – vlek se mezitím exportoval s `--no-bake`). Mini a drony sedí. Oprava = jeden plný
export Middle a Maxe (s cache pečení teď stojí jen jednou).

### Časy (Middle / Max / Mini, headless, BelowNormal, bake na GPU OptiX)

| běh | Middle | Max | Mini |
|---|---|---|---|
| bez knihovny, bez bake: stavba / celkem | 11 s / 60 s | 21 s / 90 s | 6 s / 23 s |
| knihovna studená (všechny díly se staví): stavba | 19 s (12 dílů 9,4 s) | 29 s (14 dílů 10,8 s) | 8 s (4 díly 2,9 s) |
| bake (GPU) | ~160 s | 209 s | 50 s |
| plný export, všechno studené | 226 s | 308 s | 73 s |
| **opakovaně beze změny** (díly i vmask z cache) | **60 s** | **89 s** | **22 s** |
| změna zdroje jednoho dílu (centrála), stavba | 10 s (přestaví se jen centrála, 0,75 s) | | |

Úspora opakovaného exportu je skoro celá z cache pečení (2,5–3,5 min na vlek). Změna **geometrie** jednoho dílu ale mění
DirtUV celého vleku (globální balení), takže vmask se peče znovu – to knihovna neodstraní (viz pravidlo 4).

### Drony (příprava, neimplementováno)

Dron by byl díl `build_drone.build_variant(prefix, varianta, poloha plošiny, natočení, složený)` stavěný rovnou na plošině
(pravidlo 1), stejná funkce v poloze 0 a složená by dala model předmětu „složený dron“ (`NAVRH-dron-predmet.md`).
Pozor: uzly skládání, listy, kamery a světla jsou v i3dMappings a v `foldPart`/`navLight` XML (jména se nesmí změnit),
`place_drone` dnes počítá polohu z modulových konstant vleku (musí jít parametrem) a vmask dronu je vlastní atlas `__D`.

## 7. Jeden model na díl: lokální počátek a umístění (2026-10-23, druhá etapa)

Pravidlo 1 z prototypu („díl se staví na svém místě“) platí už jen pro díly, které jsou z podstaty vázané na rám (viz níž). Ostatní se
staví **jednou v lokálním počátku** a vlek je jen umístí. Rovnocennost už není bajt po bajtu (UV0 kvádrů se počítá z polohy při
stavbě, takže detailní textura sedí o posun jinak; DirtUV a vmask se po sestavení stejně přepočítají), ale je ověřená po vrcholech,
uzlech, jménech a materiálech (níž).

### API knihovny (`blender/parts_lib.py`)

- `PL.call(fn, *args, at=Place, rename=fn, **kwargs)`: stavba v podprocesu, cache, připojení, umístění. Parametry funkce dílu jsou jen
  to, v čem se díl opravdu liší (varianta, objem, rozměr), ne poloha.
- `PL.Place(matice, mirror_x=False)` a `PL.Place.at(x, y, z, rot_z=0, mirror_x=False)`: nejdřív případné zrcadlení podle roviny x = 0
  (obrátí se plochy a UV každé plochy zpět, takže nápisy a nálepky zůstanou čitelné), pak matice. Sloučené meshe (matice objektu je
  jednotková) se přepíšou do vrcholů, ostatní objekty dostanou matici; zrcadlení se vždy zapisuje do vrcholů (zrcadlení uzlu
  s potomky zatím není). Polohy (`Vector`) ve výsledku funkce se po umístění převedou, skalární výšky ne (volající si je přičte).
- `rename(jméno)`: vlek si dílu přidělí jména podle místa (`Rim_1L`, `battery3M`, `Gen_1_*`, `generatorExhaust2`); přejmenují se objekty
  i data meshů.
- `PL.localize(anchor)`: pro funkci dílu, která staví v souřadnicích vozidla (mlýnek): na konci posune vše o `-anchor`, takže díl leží
  ve svém počátku a vozidlo ho umístí `Place.at(*anchor)`.
- `PL.join_meshes(jméno, objekty)`: spojí díly do jednoho meshe (materiály v pořadí prvního použití); pumpa a násypka se z dílů skládají
  zpátky do jediného meshe `waterPump_vis` / `limeHopper_vis`, takže uzly a mapování v XML zůstávají.
- `POSITION_CONSTANTS` (`sdt_tanks.PUMP_XY`, `INDUCTION_XY`): konstanty s polohou, které Max přepisuje, se nezapočítávají do platnosti
  cache (jinak by se díl při každém přepnutí vleku stavěl znovu).
- Funkce spouštěné přes `exec` (headless, katalog) se do podprocesu předávají podle souboru (`module_of`).

### Co se změnilo ve vlecích

| díl | dřív | teď |
|---|---|---|
| centrála | tři sady (Middle, Max zrcadlená, Mini otočená), polohy v parametrech | **jedna** funkce `build_generator(rear_socket)`: Middle a Mini sdílejí stejný díl (posun, Mini navíc otočení −90°), Max používá variantu s průchodkou kabelu a staví ji dvakrát, druhou zrcadlově |
| indukční nádrž, čerpadlo, vápenná nádobka, mixér | pozice v parametrech | stavba v počátku, `Place.at(...)`; indukční nádrž má dvě skutečné varianty (`hose_inlet`) |
| tažný věšák | `y_rear` v parametru | stavba v počátku, posun na záď Maxu; výška spodku nosníku zůstává parametr (mění nožky) |
| disky a pneu | jeden díl na kolo (jméno a strana v parametrech) | jeden díl na rozměr, pravé kolo je zrcadlový obraz levého (`Place(mirror_x=True)`), jméno přes `rename` |
| baterie | `P.battery` volaná 18× přímo | tři díly (S, M, L), jména `battery<k><S/M/L>` přes `rename` |
| hlavní nádrže | `build_main_tanks(z)` | beze změny: jejich poloha v rámu Middle je součást dílu (jen Middle) |

**Proč Max nepoužívá otočení o 180° místo zrcadlení** (zadání ho preferovalo): druhá centrála Maxu má panel a nádrž na vnější straně,
kabelovou průchodku na zadní stěně (kabel jde k nabíječce vzadu) a ústí výfuku dopředu. Otočení o 180° by nádrž i kabel přeneslo
dopředu a výfuk by mířil dozadu, takže by se měnil tvar vleku i vedení kabelů (`GEN_CABLE_ENDS`). Zůstává zrcadlení jedním dílem,
nálepky a nápisy jsou díky obrácení UV čitelné (v GE ověřeno na obou variantách).

### Díly knihovny (karta v katalogu = jeden díl, 39 karet, 60 variant)

| skupina | díly (id v katalogu) | varianty |
|---|---|---|
| Elektrocentrála a rozvody | `part_generator`, `part_mixer` | centrála: zásuvka nabíječky na boku (Middle, Mini) / zadní průchodka kabelu (Max ×2) |
| Nádrže a čerpadla | `part_main_tanks`, `part_induction_tank`, `part_pump_unit`, `part_lime_vessel`, `part_rear_hitch` | hlavní nádrže 800–5 000 l; indukční nádrž základní / s přívodem plnicí hadice |
| Kola | `part_rim`, `part_tire` | disky R15, R22; tři rozměry pneu |
| Mlýnek | `part_mill_chassis`, `_drawbar`, `_hopper`, `_auger`, `_mill`, `_engine`, `_fuel_tank`, `_bin`, `_control_box`, `_deck_details`, `_port_cap`, `_extra_details`, `_hose_reel`, `_hose_stored` | – |
| Pumpa a násypka | `part_pump_frame`, `_engine`, `_tank`, `_head`, `_strainer`, `part_hopper_frame`, `_funnel`, `_feeder`, `_labels`, `part_hose_end` | motor a nádrž jsou společné pumpě i násypce |
| Dron | `part_drone_fuselage`, `_tank`, `_arm`, `_rotor`, `_gear` | velikost S, M, L |
| Baterie | `part_battery` | S (DB800), M (DB1560), L (DB2160) |

- Mlýnek (`sdt_mlyn.part_*`): všechny `build_*` funkce kromě kol (ta jsou díly disku a pneu); drobnosti se přidružily k nosnému dílu
  (nádoba + `build_hopper_detail`, mlýn + `build_mill_detail`, motor + `build_engine_detail`, rám + pruhy). Palivová nádrž se
  oddělila od motoru. Vozík se z nich skládá v `sdt_mlyn.build_all` (jen pořadí uzlů v kolekci se mírně změnilo). `hose_reel` a
  `hose_stored` jsou starší návrh, který vozík dnes nestaví; zůstaly v knihovně a v katalogu.
- Pumpa a násypka (`build_pump.part_*`, `build_hopper.part_*`): složené zpátky do jednoho meshe, mesh je bit po bitu stejný jako dřív.
  Koncovky hadic pumpy jsou díly `part_hose_end` a `part_strainer`.
- Dron (`build_drone.part_*`): jen pro katalog a export dílů; vlek dál staví dron přes `build_drone.build_drone` (export dronů se
  nemění). Všech pět dílů je ve stejné souřadné soustavě (rozložený letový stav, počátek na zemi pod středem trupu), takže složené
  dají dron. Rameno je třetí (má trysku u všech velikostí), vrtule jeho listy (u M a L souosé čtyři).
- Baterii používá Middle (Max a Mini ji přebírají).

### Ověření rovnocennosti (tmp/dily: `dump_scene.py`, `compare_dump.py`, `build_export.py`, `compare_i3d.py`)

Základ je stavba z `git HEAD` (před změnami), srovnání po každém kroku.
- **Scéna** (vrcholy všech meshů ve světě, rodiče, typy, materiály, vlastnosti, kolekce a pořadí objektů): Mini 845 objektů, Middle
  1 575, Max 2 356, pumpa 193 a násypka 10 jsou shodné, největší odchylka vrcholu 7·10⁻⁷ m (pumpa a násypka 0). Mlýnek (49 objektů):
  geometrie, jména a materiály shodné do 6·10⁻⁸ m, liší se jen pořadí objektů v kolekci (díly se připojují po skupinách). Pravé disky:
  zrcadlený díl má stejnou množinu vrcholů jako dřív stavěný pravý, jen v jiném pořadí (porovnáno jako množina).
- **Export do tmp** (`--no-bake`, bez pečení vmask): počet uzlů shodný (Mini 841, Middle 1 567, Max 2 348, mlýnek 45), všechny cesty a jména
  uzlů shodné, všechny materiály včetně textur shodné, **XML vleků Mini, Middle a Max bajtově shodné s módem** (včetně všech
  `i3dMapping`), XML mlýnku se liší jen ručně přidaným řádkem `bagOutput` v módu (není v šabloně). Atributy uzlů: Middle a Max mají
  jeden rozdíl (`limeValveLever_Lever`: jiný rozklad stejné polohy na posun uzlu a vrcholy, pivot `limeValveLever` stojí stejně, takže se
  páka otáčí stejně) a Mini deset (každý mesh centrály nese teď tvar ve vrcholech, dřív otočení −90° v uzlu; světová poloha je stejná,
  ověřeno srovnáním scény).
- Do `mod/` jsem nic neexportoval.

## 8. Foto v GIANTS Editoru (GE) a katalog

Katalog ukazuje **jen snímky z GE** (z i3d, jak je načte engine hry). Blender se použije jen u stavů, které v GE nejdou nafotit:
rozložený stav vleků a dronů vzniká animací ve hře a v editoru není (karta u něj píše „Blender“).

1. Data o modelech a dílech: `python tools/katalog.py` (Blender, bez okna; zároveň vyrenderuje rozložené stavy). Úloha `dily`
   (`blender/catalog_render.py`) sestaví karty dílů z knihovny a z volání v jednotlivých vlecích (`parts_lib.stats["calls"]`).
2. Díly do i3d: `blender.exe -b --factory-startup --python blender\export_parts.py` → `tmp/ge/parts/<díl>[__<varianta>].i3d`
   (komunitní exportér GIANTS, vehicleShader, DirtUV, `default_vmask`, atlas nálepek v `tmp/ge/parts/textures`; jen pro GE, do módu nic).
3. Vozidla a objekty: `python tools/ge_prepare.py` → `tmp/ge/models/<id>/<původní jméno>.i3d`: kopie i3d z módu se skrytými tvary,
   které katalog neukazuje (kolize, plnicí tvary, články hadic, varianty mimo výchozí konfiguraci, u dronů a baterií vše ostatní),
   absolutní cesty k texturám a `.shapes` jako pevný odkaz. Soubor musí zůstat pod původním jménem (`.shapes` se hledá podle jména i3d).
   Originál v módu se nemění a v GE se nic neukládá.
4. Plán záběrů: `python tools/ge_plan.py --batches 4` napíše `tmp/ge/batch_NN.lua` (4 položky po 16 pohledech). Vzdálenost kamery se
   počítá z ~6 000 vzorků vrcholů (ne z bboxu) tak, aby model zabral ~74 % záběru; `FILL_ITEM` zmenšuje záběr u dronu M.
5. V GE (Scripts → GE-MCP Bridge, `ping_editor`): jednorázově světla a pomocné funkce, pak `source(batch)` v `run_lua`
   (`force=true`; `dofile` v GE není). Model si maže funkce sama.

```lua
-- světla (jednou): směrová, key -50°/35° 4, fill -25°/-140° 1.6, shora 1.2, zespodu 80° 1.3
local function mk(name, i, rx, ry) local l = createLightSource(name, 0, i, i, i, 1000); link(getRootNode(), l); setRotation(l, math.rad(rx), math.rad(ry), 0) end
mk("sdtKey", 4, -50, 35); mk("sdtFill", 1.6, -25, -140); mk("sdtTop", 1.2, -85, 0); mk("sdtBottom", 1.3, 80, 0)
function sdtLoad(path) local id = loadI3DFile(path, false, false, false); if id == nil or id == 0 then return 0 end; link(getRootNode(), id); return id end
function sdtDrop(id) if id ~= nil and id ~= 0 then delete(id) end end
function sdtShots(name, cx, cy, cz, ...)           -- {pohled, azimut, sklon, vzdálenost}
  local cam = getCamera()
  for _, v in ipairs({...}) do
    local y, p, dist = math.rad(v[2]), math.rad(v[3]), v[4]
    local dx, dy, dz = math.sin(y) * math.cos(p), math.sin(p), math.cos(y) * math.cos(p)
    setWorldTranslation(cam, cx + dx * dist, cy + dy * dist, cz + dz * dist)
    if math.abs(v[3]) > 80 then setDirection(cam, dx, dy, dz, 0, 0, -1) else setDirection(cam, dx, dy, dz, 0, 1, 0) end
    renderScreenshot("E:/.../out/ge/" .. name .. "_" .. v[1] .. ".png", 1280, 960, 1280 / 960, "srgb", 0, 0.26, 0.27, 0.29, 1.0, 3, 12, true)
  end
end
```

   Čtyři floaty v `renderScreenshot` jsou barva pozadí (s nulami je pozadí černé a černé rámy zmizí). 64 snímků v jednom volání
   (4 položky) bridge unesl; dřív se zasekl jeden `run_lua` s 16 rendery spojený s vytvořením světla. Azimut 0 = zepředu, kladný doleva,
   sklon nahoru; i3d souřadnice jsou (x, z, −y) z Blenderu.
6. `python tools/katalog.py --page`: PNG → JPG 1 280 px (q76) a náhledy 400 px do `out/katalog/img`, `thumb`, stránka. Nasazení podle
   skillu `/static-pages` (`E:\ClaudeProjects\StaticWeb\sites\sdt-katalog`, URL `https://fs25-relay.tail372622.ts.net/static/sdt-katalog/`).

Výsledek: 79 položek v GE (19 modelů z módu + 60 variant dílů) po 16 pohledech = 1 264 snímků, k nim 48 Blender snímků rozložených
stavů; stránka má 58 karet (3 vleky, 3 drony, 39 dílů, 13 objektů) a ~49 MB (`img` 40 MB, `thumb` 9 MB).

### Co v GE nejde nebo se liší od hry

- Rozložený stav (animace skriptem) a skládání dronů: jen Blender.
- Skriptové uzly (články hadic, koncovky) jsou skryté, plnicí a kolizní tvary taky. Špína a opotřebení (vmask) chybí, u dílů je
  vanilla `default_vmask` a vlastní DirtUV.
- Světlo je z editoru (4 směrová světla, šedé pozadí), proto některé světlé plochy přesvítí (pytel, bílé nádrže).
- Dron M v exportovaném i3d má víc vyložené listy než model v katalogu, proto má menší záběr.
- Detaily (skříň, žebřík…) z dřívější verze katalogu v GE nejsou; pohledy 45° je nahrazují.
