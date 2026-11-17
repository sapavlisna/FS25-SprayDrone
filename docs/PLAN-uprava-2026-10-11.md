# Plán úprav 2026-10-11 (Mini, Middle, Max + průřezové body)

Zdroj: Pavlova zpětná vazba po hře (snímky Mini + Utili Trailer 2 a Farmtech DPW 1800). Ve hře nic z toho zatím neověřeno.
Ladění: `savegame12` (nová malá mapa, všechny vleky koupené). Do savu se z Claude nesahá (klasifikátor oprávnění to blokuje).

## Zdroje vzorů (jen číst, nic z nich nekopírovat do módu bez převodu)

- **Utili Trailer 2** (Lizard, mód `E:\SteamLibrary\FS25-Mods\FS25_UtiliTrailer\utiliTrailer2.i3d` + xml): podvozek, kola, blatníky, nájezdová brzda pro Mini
  a inspirace kolama/podvozkem pro Middle.
- **Farmtech DPW 1800** (vanilla `E:\SteamLibrary\steamapps\common\Farming Simulator 25\data\vehicles\farmtech\dpw1800\dpw1800.xml/.i3d`): oj pro Max
  (kopie tvaru, pevná, bez předních kol/otočné nápravy).
- Vanilla kola/pneu: `$data/shared/wheels/...`, tireCategory `TRAILER` / `TRUCK`, vanilla `wheelConfigurations` s výběrem značky (Trelleborg, …).

## Proudy (každý vlastní soubory; sdílené soubory před úpravou znovu přečíst)

### A — Mini (Blender + Pad)
Vlastní: `blender/build_trailer_mini.py`, `export_mini_mod.py`, `headless_mini.py`, `templates/sprayDroneTrailerMini.xml.in` (mimo `wheelConfigurations`),
`scripts/SprayDronePad.lua`, `.blend` Mini.
1. **Podvozek z Utili Trailer 2**: kola, blatníky, náprava/pružení, tvar rámu a oj podle módu (min. kola); jen vizuál, kola generuje hra z konfigurace.
2. **Výtlačná trubka čerpadla → navíječ po zemi**: ne přes nádrž nahoře, ale nízko při palubě (pod/vedle nádrže); zkontrolovat kolize s bednami, hadicí a navíječem.
3. **Boční stěny bedny s dronem místo plachet**: plechové panely, které se po rozložení vyklopí bokem na zem (zavěšené dole/nahoře na bočním čepu),
   pak pochozí/rámová plošina; padající pomačkaná plachta se ruší (`padTarpL/R`, `padTarpCrumpleL/R`, `applyTarp`). Panely se nesmí protnout s dronem,
   nožičkami ani lemem (BVH kontrola jako dřív).
4. **Víc polepů** na plechových stěnách a bedně (dron, nápisy, výstražné pásy); atlas jen přes zámek (viz Sdílené).

### B — Middle (Blender, základ pro Mini/Max!)
Vlastní: `blender/build_trailer_middle.py`, `export_middle_mod.py`, `headless_middle.py`, `templates/sprayDroneTrailerMiddle.xml.in` (mimo `wheelConfigurations`),
`scripts/SprayDroneLadder.lua`, `check_ladder.py`, `.blend` Middle.
**Pozor:** Mini a Max se staví z `build_trailer_middle.py` (exec + textové patche) — nepřejmenovávat funkce/konstanty a po změně přebuildit Mini i Max (regrese).
1. **Nálepky na zadní stěně skříně s kanystry větší a víc** (popisky/ikony, čitelné z odstupu).
2. **Inspirace podvozkem a koly z Utili Trailer 2** (vzhled kol/blatníků/rámu; stávající stav „není špatný" — jen vylepšit).
3. **Zkrátit vůz**, když vzadu nemusí být místo na bednu s dronem; ověřit, že na plošině zůstane místo na dron (odpověď Pavlovi: je/není místo na další dron vzadu).
4. **Žebřík dopředu a sklopný**: celý posunout k přednímu rohu (kde je teď kolo s hadicí → navíječ/hadici případně přesunout), složený vzpřímeně
   podél boku; rozložený = jen otočení kolem bodu v horní části (žádné vysouvání, žádný `ladderSlide`), dolní konec dosedá na zem. Hadice/navíječ nesmí kolidovat s rozloženým žebříkem,
   `colLadder` a spouštěč lezení (`ladderTrigger`) se posunou s ním. `build_ladder` udělat parametrický (pozice, výška), aby ho Max převzal (viz F).

5. **Roleta skříně na kanystry (Middle i Max, `build_canister_cabinet`)**: nesmršťovat (`scale.y` 1 → 0,02), ale **vyjet nahoru** a zmizet v pouzdře roletové schránky nad otvorem
   (pouzdro s válcem navrchu otvoru, kde se roleta „srolovává“; animace rolování není nutná, panel se jen posune nahoru za/do pouzdra). Do šablon dát `doorTravel` (m, o kolik panel vyjede) —
   Lua (proud C) pak posune uzel `Toolbox_Door` místo škálování. Pouzdro nesmí kolidovat se stropem skříně, žebříkem ani popisky; kolize a vsávací otvor kanystrů zůstávají.
6. **Polohovatelné nohy (Middle)**: čtyři nohy `trailerLeg1-4` (pivot na rámu, tyč `trailerLegRod<i>` pohyblivá po lokální ose dolů, patka `trailerLegFoot<i>`; ve složeném/zasunutém stavu zasunuté nad zemí),
   rozumně umístěné u rohů rámu (u Middle přední nohy za ojí/opěrným kolečkem, nesmí kolidovat s kolem, žebříkem ani hadicí). Logiku (Lua) dělá proud F.

### C — Průřezové Lua/XML (bez Blenderu)
Vlastní: `scripts/SprayDroneToolbox.lua`, `scripts/events/SprayDroneToolboxEvent.lua`, `SprayDroneStation.lua` (jen plnění vody / vyprazdňování), překlady,
`wheelConfigurations` bloky ve všech třech šablonách `blender/templates/*.xml.in`, `tools/prepare_testsave.py`.
1. **Bedny na kanystry se samy nezavírají**: zrušit zavření po nečinnosti (`OPEN_TIMEOUT_MS`) a při vzdálení hráče (`updateOpenTimeout`);
   zavře je jen hráč (klik) — Pavel: „chyba, že se samy zavřou, když odejdu". Mini (2 bedny) i skříň Middle/Max (vrata).
2. **Voda přes R jen u zdroje vody**: zjistit, jak dnes R doplňuje vodu (vanilla `FillActivatable` / `exactFillRootNode`, docs zmiňují `SprayDroneWaterActivatable`,
   v kódu už není); cíl = vanilla mechanika `waterTrailer` (nádrž se plní z vodní plochy/zdroje poblíž), nic „z ničeho". Fungovat u všech tří vleků.
5. **Ctrl+I (vanilla `TOGGLE_TIPSTATE_GROUND`) vyprázdní koncentrát**: u všech tří vleků jde koncentrované tekuté hnojivo a koncentrovaný herbicid
   (fillUnit koncentrátu, `SDT_CONCENTRATE_*`) vypustit na zem — dischargeable s `dischargeNode` u hrdla/ventilu, `canDischargeToGround`; ověřit, že se
   při vypouštění odečítá fillLevel a nelije se uvnitř vleku. (Případně i hlavní nádrž, pokud je to vanilla rozumné.)
6. **Výběr pneu**: u Mini/Middle `tireCategories="TRAILER"`, u Max `TRUCK` — nabídnout v konfiguraci více vanilla pneu (Trelleborg, …) místo jedné
   `DEFAULT`, ať si hráč vybere. Dbát na `saveId` (viz Upozornění). Modelovaná kola v Blenderu zůstanou jen náhled.

7. **Roleta**: `Toolbox_Door` při otevření vyjede nahoru o `doorTravel` (translace podél lokální osy uzlu/vozidla Y; atribut v `<toolbox>`, výchozí zachová škálování, ať nic nespadne) — nesmršťovat.
8. **Zvuky** (vzorky vanilla z `$data/sounds/...`, `<sounds>` v šabloně / `SprayDroneSound.lua`, vzor existujících `generator`/`pump`): roleta nahoru/dolů, otevření/zavření bedny (víko Mini, vrata skříně),
   doplňování vody, koncentrátu a nafty (nalévání z kanystru, plnění vodou, přečerpání), rozkládání a skládání vleků (všechny tři, včetně panelů/pad Mini, žebříku, nohou).
   Zvuky jen na klientech v dosahu, smyčky se zastaví při konci akce; bez vzorku vlek mlčí (nil-bezpečné).

### D — Max (Blender)
Vlastní: `blender/build_trailer_max.py`, `export_max_mod.py`, `headless_max.py`, `templates/sprayDroneTrailerMax.xml.in` (mimo `wheelConfigurations`), `.blend` Max.
1. **Oj podle DPW 1800**: tvar a proporce oje (tažné oko, rám) převzít z vanilla DPW 1800, ale **pevnou** a **bez předních kol** (bez otočné nápravy/rudle). Pozor na `attacherJoint`.
2. **Nádrže**: kulaté (válcové) nebo vozík zkrátit / líp vycentrovat (nádrže nyní nevypadají dobře); zachovat objemy, hrdla, kolize `colTank*`.
3. **Bedna s hadicí k zadnímu dronu** přesunout vedle nabíječky, ze **druhé strany** než je bedna k přednímu dronu (zrcadlově).
4. **Kola**: skutečná vanilla kola (TRUCK), výběr značky (Trelleborg…) — konfigurace řeší C, D dělá model náhledu + `tireCombination`.
5. **Žebřík** (po dokončení B 4): doprostřed vleku, sklopný dolů jako u Middle (otočný kolem horního bodu, bez vysouvání), klidně menší, končí nad blatníky.

6. **Polohovatelné nohy (Max)**: čtyři nohy jako u Middle (stejné názvy uzlů `trailerLeg1-4`, `trailerLegRod<i>`, `trailerLegFoot<i>`), u rohů rámu mimo tandem a oj. Logiku dělá proud F.
7. **Roleta skříně** je společný kód (`build_canister_cabinet` v middle) — dělá proud B; D jen ověří, že Max po změně staví.

### F — Vyrovnání vleku nohama (Lua, po B a D)
Vlastní: nový `scripts/SprayDroneLevel.lua` (nebo část `SprayDroneStation.lua` jen pro rozkládání), `modDesc.xml` (registrace), šablony Middle/Max (jen blok legs v `<sprayDrone>`).
1. Při rozložení se nohy `trailerLeg1-4` vysunou na terén (zjištění výšky terénu pod patkami, jako `SprayDronePad` u Mini) a vlek se **vyrovná do roviny** (vodorovná paluba v obou osách).
2. **Rozumný limit náklonu** (nastavitelný atribut, výchozí řádově ±8° podélně i příčně, max délka nohy z modelu). Pokud nelze vyrovnat (nad limit / noha nedosáhne), **vlek nejde rozložit** a hráč dostane hlášku
   (vzor `SprayDronePad.checkDeploy` / `maxLegLength`, `maxHeightDiff`); zablokovat `getIsFoldAllowed` ve směru rozkládání.
3. Multiplayer (stav v `writeState`), uložení, zvuk (viz C 8). Nohy se zasunou před složením.

### E — Kontrola na konec (po A–D)
Sériově, jeden agent:
1. **Kolize všude** (Mini, Middle, Max): kolizní kvádry proti novým dílům, `check_xml_nodes.py`, BVH průniky pohyblivých dílů (žebřík, panely, víka), kolize nezasahují do pochozích míst.
2. **Poloha vrtulí u všech tří dronů** (S/M/L, `Drone_S_/Drone_A_/Drone_L_`): rotory nad rameny, souosé páry, nic neprotíná trup; podle DJI Agras T25/T50/T100 (rozměry v `docs/PLAN-0.9.md`).
3. Přebuildit a exportovat všechny tři (`headless_*.py -- build export`), `validate_mod.py`, `lua_check.py`, `check_xml_nodes.py`, `tmp/test_toolbox_parts.py`.
4. Aktualizovat `docs/DRON.md` (jen stav, ne historii) a napsat předávací poznámku: co ověřit ve hře v `savegame12`.

## Sdílené / pravidla pro agenty

- **Atlas polepů** (`tools/make_decal_atlas.py`, `blender/decal_layout.py`, `blender/textures/sdt_decals.png`, `mod/.../textures/sdt_decals.dds`) smí v jednu chvíli regenerovat jen jeden agent:
  před spuštěním `mkdir tmp/atlas.lock` (neexistuje-li, smíš), po skončení `rmdir tmp/atlas.lock`; existuje-li, počkej (15 s) a zkus znovu.
  Do `decal_layout.py` přidávat jen vlastní nové regiony, cizí neměnit.
- Každý trailer má vlastní `.blend` a vlastní `out/` / `tmp/<stream>/` podsložku pro pracovní soubory. Žádné soubory mimo projekt.
- Blender: `E:\FS25-edit\blender-5.1.2-windows-x64\blender.exe -b --python blender\headless_<mini|middle|max>.py -- build|render|export`.
- Hra se nespouští, savegame se needituje.
- Žádný commit (jen Pavel výslovně). Každý agent na konci: co změnil, co je neověřené ve hře, co další proud musí vědět.
- Lua: styl okolního kódu, `tools/lua_check.py` po úpravě.

## Pořadí

1. Paralelně **A, B, C, D** (D bez bodu 5 a bez Lua nohou). Roleta (B 5 geometrie + C 7 Lua) se domluví přes atribut `doorTravel`. Konflikty: B mění `build_trailer_middle.py`, na kterém stojí A a D → B nesmí měnit signatury, A/D nesmí
   editovat `build_trailer_middle.py` (potřebují-li změnu, napíšou ji do poznámky).
2. Po B: D bod 5 (žebřík Max).
3. Po B a D: **F** (Lua nohou, vyrovnání).
4. Poté **E** (zahrnout i nohy a rolety do kolizí).

## Upozornění

- Změna pneu/konfigurací kol po zápisu `saveId` rozbije uložené vleky (kola chybí, viz paměť `reference_fs25_wheel_config_save`). Ponechat `saveId="DEFAULT"` jako
  výchozí konfiguraci, nové přidat pod novými saveId, a **Pavlovi říct, co se v savu změní**.
- Mini nádrž je 300 l (`TANK300`), starý save s `TANK450` je neplatný (viz výše).

## Stav (konec proudu E, 2026-10-11)

Nic z úprav nebylo ve hře ověřeno. Ověřeno jen: Blender (build + export všech tří vleků, BVH kontroly), `tools/validate_mod.py`, `check_xml_nodes.py`, `lua_check.py`, offline Lua testy a čtení savegame12.

### Nástroje

- `tools/check_all.py [--no-build] [--only mini middle max] [--save 12]` — jeden příkaz: build + export všech tří vleků v Blenderu (`headless_<vlek>.py -- build export`), `validate_mod`, `check_xml_nodes`,
  `lua_check`, `audit_spec_fields`, `test_split` / `test_mixer` / `test_headlands`, `tmp/test_toolbox_parts.py` a `check_save`. Výstup OK / CHYBA / ZNÁMÉ (chyba XSD „sprayDrone not expected“ je známá). Plný běh trvá ~30 min
  (export baká textury), `--no-build` pár sekund. Hlášku Blenderu o odhlášení cizího doplňku při ukončení (`blender_i3d_importer`, `UnboundLocalError`) ignoruje.
- `tools/check_save.py [slot]` — jen čte `vehicles.xml` savegame a porovná id konfigurací vleků módu (kola, nádrže, …) s XML módu. Tady: 28 vleků v savegame12 sedí.
- Geometrické kontroly v Blenderu (ručně, `blender.exe -b <vlek>.blend --python <skript> -- <vlek>`, nejsou v `check_all`): `blender/check_ladder.py` (žebřík ve všech krocích animace), `tmp/e/check_col.py` (kolizní kvádry vs viditelná geometrie, vyplnění, rozměry),
  `tmp/e/check_door.py` (roleta skříně v 5 krocích otevření), `tmp/e/check_timeline.py` (žebřík × nohy × vlek v čase skládání), `tmp/e/check_rotors.py` (vrtule dronů: poloha, souosost, 36 poloh listů proti trupu, ramenům, tryskám),
  `tmp/e/check_i3d_rotors.py` (totéž v exportovaném i3d), `tmp/mini/pa/check_panels.py` (panely a boční stěny Mini), `tmp/middle/check_legs.py`, `tmp/max/check_bvh.py`.

### Hotovo

- **Mini**: podvozek podle Utili Trailer 2 (kola vně rámu, blatníky, listové pružiny, šířka 2,60 m), výtlak čerpadla nízko při palubě, boční plechové stěny s polepem místo plachet (Lua `SprayDronePad.applySide`), víc polepů.
- **Middle**: vůz kratší (6,07 m místo 6,37), větší a víc nálepek na vratech skříně, vzhled kol a blatníků podle Utili Trailer 2, sklopný žebřík u pravého předního rohu (kolem čepu o 10°, bez vysouvání), roleta skříně vyjíždí nahoru do pouzdra, čtyři nohy.
- **Max**: oj podle DPW 1800 (pevná, bez kol), oválné nádrže, druhý navíječ vedle truhly nabíječky, skutečná kola TRUCK s výběrem značky, žebřík, roleta, čtyři nohy.
- **Lua / XML**: bedny se samy nezavírají, voda přes R jen u hladiny (`waterTrailer`), Ctrl+I vypouští koncentrát, zvuky (roleta, víka, lití, plnění, skládání/rozkládání), výběr pneu, `SprayDroneLevel.lua` (nohy: vysunutí na terén, kontrola náklonu a dosahu před rozložením).
- **Proud E (nálezy a opravy)**:
  - `audit_spec_fields`: `spec.pumpCapChecked` a `spec.pumpTankTarget` jsou stav **jednoho dronu** (plnění čerpadlem, `setState` je nuluje; na Maxu má každý dron vlastní) a kód běží v kontextu dronu (`updateDroneLogic` přes `forEach`) → do seznamu `drone`;
    `spec.level` (nohy) je stav vozidla → do seznamu `shared`.
  - Dron L: výložník s tryskou visel v rovině spodního rotoru (listy by trysku a nosník metly) → výložník a tryska pod spodním rotorem, hadice sestupuje osou motoru; `effects#nozzleY` L −0,12 → −0,24 (Middle i Max šablona).
  - Dron M (T50): rozteč motorů byla 1,59 × 1,90 m, což je rozměr DJI se SLOŽENÝMI vrtulemi; podle rozměru s rozloženými vrtulemi (2800 × 3085 mm) a průměru 1375 mm vychází 1,425 × 1,71 m (S a L se tak počítaly už dřív).
  - Plnicí hrdlo dronu: o 4 mm níž (složený list vrtule S zajížděl do jantarového lemu).
  - Žebřík: patka rozloženého žebříku 7 cm nad zemí (`LADDER_FOOT_Z`, dřív 2,5 cm: svisle složený žebřík zajížděl 3 cm pod terén).
  - `export_middle_mod.png2dds`: výstup převodu dekódovaný jako UTF-8 s `errors="replace"` (jinak vypisoval výjimky vláken při každém exportu).
  - Kolize: všechny col* kvádry sedí na modelu, `<size>` / `lengthOffset` odpovídají obrysu modelu (Mini 2,60 × 5,99 × 1,66 / 1,52, Middle 2,32 × 6,07 × 3,51 / 0,58, Max 3,09 × 9,83 × 3,85 / −1,79).
    Bedna Mini (panely, boční stěny, nožičky), nohy a pouzdro rolety kolizi záměrně nemají (rozkládají se / pohybují se, statický kvádr by zůstal na místě).
  - Žebřík, nohy, roleta, panely Mini, víka Mini, vrtule všech tří dronů: žádný průnik v kontrolovaných polohách (viz „Ověřeno“ v `docs/DRON.md`).
    `tmp/max/check_bvh.py` hlásí u Maxu jen konstrukční dotyky (desky noh na rámu a odrazkových páscích, stěny kapes navíječů v řezech horní desky, spoje potrubí); `check_panels.py` u Mini jen plošný dotyk panelu Z se zadním nosníkem v čepu.

### Neověřeno ve hře / známé

- Vše výš. Zvlášť rizikové: rozložení Mini na nerovném terénu (boční stěny, plošina), nohy na svahu (hlášky o náklonu), nastoupení na žebřík z boku, roleta ve hře (pohyb nahoru + zmenšení), zvuky (jen vzorky vanilla, bez poslechu), nová kola (id `saveId`).
- Mini: bedna s dronem a panely nemají kolizi; hráč projde bednou (jen je-li složená).
- Obrázky obchodu a ikony vleků se při každém exportu znovu vyrenderují (Workbench, headless): zkontrolovat v obchodě, že vypadají dobře (nový Mini, dron M s kratšími rameny).

### Co otestovat ve hře (savegame12)

1. Obchod: u všech tří vleků výběr kol (Mini/Middle Trelleborg a BKT, Max Continental), výchozí `DEFAULT` zůstane; Mini 300 l; vlek v dílně přepnout kola. **Vleky v savegame12** s id kol `DEFAULT_…` se načtou (zkontrolováno `check_save.py`); starý Mini s `TANK450` je neplatný.
2. Mini: zapřáhnout, rozložit (`X`): boční stěny se vyklopí na zem vedle vleku (i na svahu, spodní hrana nad terénem), panely do plošiny, nožičky, dron přejede, vzlet a přistání na H, složit zpět; šířka 2,60 m při jízdě a couvání za tahačem, blatníky, výtlačná trubka při palubě, víka beden.
3. Middle: rozložit: nohy se vysunou na terén (na svahu 3–5°, na stráni nad 8° musí vlek odmítnout rozložení s hláškou), žebřík se sklopí (10° ven, patky nad zemí), dron se rozloží; vylézt po žebříku z boku na horní desku a zpět; složit zpět (žebřík i nohy).
4. Skříň na kanystry (Middle, Max): otevřít klikem, roleta vyjede nahoru do pouzdra a zmizí, zavřít klikem; bedna se po odchodu sama nezavře; vsátí a výdej kanystru; zvuk rolety.
5. Max: oj (zapřáhnout za velký traktor, zatáčka), oválné nádrže, dva navíječe a dvě hadice při plnění obou dronů, nohy (přední y −0,75, zadní za tandemem), žebřík u předního blatníku tandemu.
6. Voda: napuštění přes R jen u vodní plochy (jinde nic), u všech tří vleků; Ctrl+I vypustí koncentrát na zem (ubývá z nádrže koncentrátu, nic neteče do vleku); zvuky nalévání, plnění, přečerpání, skládání.
7. Drony: M (kratší ramena) i L (tryska pod spodním rotorem): rozložení, roztočení, vzlet, postřik (mlha z trysek L je nyní o 12 cm níž), složení.
