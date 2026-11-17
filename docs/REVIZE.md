# Revize módu FS25_SprayDroneTrailer (zadání pro řídícího agenta a subagenty)

Založeno 2026-10-04. Cíl od Pavla: projít celý mód (všechny tři vleky Car / Mini / Max, všechny velikosti dronů S / M / L),
najít chyby, kolize a nesmysly v číslech, udělat refactoring a **ve hře** vyzkoušet, že se vše chová jako běžné herní mechaniky
(nabídky, popisky, zvuky, zapřažení za různé stroje). Testovat, zkoušet, opravovat — dokud to nebude dotažené.

## Společný kontext (platí pro všechny role)

- Projekt: `E:\ClaudeProjects\FS25-SprayDrone`. Mód: `mod\FS25_SprayDroneTrailer` (symlink do `E:\SteamLibrary\FS25-Mods`, hra ho čte přímo).
  Zdrojové modely: `blender\` (Python skripty `build_*.py`, `.blend`), export `export_*_mod.py`, šablony XML `blender\templates\*.xml.in`.
  **XML vozidel a i3d jsou z velké části generované exportem z Blenderu** — oprava jen ve vygenerovaném souboru se při dalším exportu ztratí.
  Opravuj v šabloně / v build skriptu, a teprve potom (nebo navíc) ve výstupu.
- Dokumentace: `PLAN.md`, `docs/DRON.md` (hlavní popis, 1200 řádků, **může být v detailech zastaralá — čísla ověřuj v kódu a XML**),
  `docs/DVA_DRONY_NAVRH.md`. Zdrojáky hry: `out\gamesource\dataS\scripts`, data hry `E:\SteamLibrary\steamapps\common\Farming Simulator 25\data`
  (nebo kde je nainstalovaná hra — dohledej přes `libraryfolder.vdf` / `steamapps`).
- Skill `fs25-modding` je k dispozici (Lua, XML, i3d, GIANTS konvence). Použij ho.
- Stav: Car (vlek za auto, 1000 l) je ve hře ověřený. **Mini a Max (včetně dvou dronů a pohledu z dronu) jsou napsané, prošly jen
  `tools/lua_check.py`, `tools/audit_spec_fields.py`, `tools/test_split.py` a nebyly ve hře.** Čekej, že tam bugy jsou.
- Existující nástroje: `tools/validate_mod.py` (chyba schématu na `<sprayDrone>` je v pořádku), `tools/lua_check.py`,
  `tools/audit_spec_fields.py`, `tools/test_split.py`, `tools/prepare_testsave.py` (volby `--trailer middle|max|mini`, `--drone none|S|M|L`, `--unfolded`, …),
  `tools/sdt_start.ps1` (start hry se slotem 11), `tools/fs25_input.ps1` (klávesy/myš/snímky), `tools/sdt_debug.ps1`. Popis testování ve hře: `docs/DRON.md`, sekce „Testování ve hře“.

## Pravidla (tvrdá)

1. Odpovídej a piš česky. Stručně, věcně. Odkazy na kód jako `soubor:řádek`.
2. **Žádné `git commit`/`push`.** Git (HEAD `d19439b`) je záloha; změny se vracejí přes `git diff` / `git checkout -- soubor` jen po dohodě s řídícím.
3. Disk `V:` je zakázaný. Nezabíjej všechny `blender.exe` (může tam být Pavlův živý Blender) — vždy filtruj podle příkazové řádky skriptu.
4. **Žádný inline kód v shellu** (`python -c`, `node -e`, heredoc): skript napiš nástrojem Write a spusť cestou. Pomocné skripty a mezivýstupy patří do `out\revize\<tvoje-role>\`
   (Fáze 2 a 3: `tmp\` projektu pro patch skripty). Nic mimo složku projektu.
5. Lua soubory mají míchané CRLF/LF (Route, Planner, Settings/Command event jsou CRLF) — nástroje a patche musí zachovat konce řádků. Po každé úpravě Lua spusť `tools/lua_check.py`
   a `tools/audit_spec_fields.py`. Pravidlo dvou dronů: funkce sahající na per-drone pole se volá jen v kontextu `runAs`/`forEach`.
6. Blender: `E:\FS25-edit\blender-5.1.2-windows-x64\blender.exe`. Build+render ~2 min (`headless_max.py -- build render`), export ~12 min → na pozadí (`run_in_background`).
   Čtení `.blend` pro audit: `blender.exe -b --factory-startup soubor.blend --python skript.py`, **nikdy neukládat**.
7. Před prací na GPU / spuštěním hry zkontroluj `nvidia-smi` a `ollama ps` (osiřelý `llama-server.exe` drží VRAM) — nespouštěj přes cizí proces.
8. Kód: žádné zbytečné komentáře (jen *proč*), žádná zpětná kompatibilita, žádné nové abstrakce/závislosti, když to jde úpravou existujícího. Nové texty vždy do `translation_cz.xml` i `translation_en.xml`.
9. Neshrnuj zbytečně. Závěrečná zpráva řídícímu max. 25 řádků: co jsi našel/udělal, kde je report, co potřebuješ rozhodnout.

## Fáze

### Fáze 1 — audit (paralelně, jen čtení; zapisuje se výhradně do `out\revize\<role>\`)

Každá role vyrobí `out\revize\<role>\REPORT.md`. Formát nálezu (tabulka nebo odrážky, jeden nález = jeden řádek/blok):

`ID | závažnost (kritická = padá/hra hlásí chybu/nehratelné · vysoká · střední · nízká) | místo (soubor:řádek / uzel) | co je špatně | důkaz (číslo, výstup, citace) | navržená oprava | riziko | odhad práce (S/M/L) | koho soubor`

Na konci reportu: „Co jsem neověřil a proč“ + „Doporučené testy ve hře“. Žádný nález bez důkazu; domněnky označ jako domněnky.

| role | úkol |
|---|---|
| **G-car**, **G-mini**, **G-max** | Geometrie a kolize modelu jednoho vleku (viz níže) |
| **K** | Kolize a fyzika ve hře (collision masky, rigid body, compound, těžiště, kola, závěsy, triggery) |
| **P** | Parametry a vyváženost (nádrže, dolet, baterie, ceny, rychlosti, hmotnosti, čerpadla, hadice) |
| **L1**, **L2** | Revize Lua kódu (chyby, MP, savegame, `runAs`, refactoring) |
| **X** | XML / i3d / překlady / obchod / zapřažení / konformita s vanilla |
| **Z** | Zvuk, efekty, světla, vzhled, HUD a nápověda (UX) |

#### G-car / G-mini / G-max — geometrie a kolize
Pro svůj vlek (`blender\build_trailer_car.py` / `_mini.py` / `_max.py`, `.blend`, `mod\…\vehicles\sprayDroneTrailer<Car|Mini|Max>\*.i3d`):
- Napiš Blender skript (`--factory-startup`, bez uložení), který projde všechny objekty a spočítá **průniky navzájem** mezi skupinami: rám/paluba, kola a blatníky, nádrže, indukční nádrž/mixér, centrála, bedna na kanystry
  a její víko/kanystry, naftový stojan, navíječe a hadice, nabíječka a šachty baterií, žebřík, opěrné kolečko, oj a tažné oko, přistávací plochy/deska, dron(y) ve složené a rozložené poloze,
  úchyty lyžin, světla, kamery dronu. Metoda: world-space AABB prefilter → přesný test (BVH `overlap` z `mathutils.bvhtree`) → vyhodnoť **objem/hloubku průniku**; ignoruj záměrné
  styky (svary, příruby, objekt posazený na desce do 5 mm) a vypiš je zvlášť.
- Totéž v **rozložené poloze** (animace `foldLadder` / `foldTrailer` na čase 0 i 1 a pro Mini mezipolohy desky D=0,3/0,6/1 podle `SprayDronePad.lua`). Pohybující se uzly (žebřík, víko bedny, deska, nožičky, dron) testuj v obou krajních polohách.
- Volné místo: kolo vs blatník (zdvih odpružení, pokud je), oj vs kola při zatáčení (tažné oko vs tahač: úhel zalomení), víko bedny při otevření vs. cokoliv nad ním, dron vs. přední/zadní hrana desky a vs. stojan/centrálu při vzletu (svislý koridor nad dronem musí být volný), hadice vs. kola.
- Pro každý reálný průnik navrhni **konkrétní posun/úpravu** (který objekt, o kolik, v kterém konstantním parametru `build_trailer_*.py`, aby nic dalšího nezasáhlo). Neprováděj ji.
- Přesnost: zapiš seznam dvojic (A, B, hloubka mm, poloha), seřazený podle hloubky. Přilož 2–4 renderové snímky nejhorších míst (`out\revize\G-<x>\*.png`) jen pokud je to levné.

#### K — kolize a fyzika ve hře
Čti i3d a XML všech tří vleků (a `SprayDroneStation/Toolbox/Pad/Ladder.lua`): `collisionMask`, `rigidBody`/`compound`/`compoundChild`, `kinematic`/`dynamic`, `mass`, `centerOfMass`, `nonRenderable`, `collisionFilterGroup/Mask`
(vzorové hodnoty: vanilla `data\vehicles\…` podobných vleků — dohledej jako reference), kola (`wheels`, `tireCategories`, rádius, `physics`, `suspTravel`, `spring`, `damper`), `attacherJoint`
(typ, `jointType`, výška, rozsah rotace — k čemu se vlek vůbec dá zapřáhnout, `lowerDistanceToGround`, `upperDistanceToGround`, `allowsJointLimitMovement`), `supportAnimation`/opěrné kolečko, triggery (nastoupení, sání bedny, hotspoty),
kolize žebříku/desky/bedny pro hráče (hráč nesmí propadat ani se zaseknout), kolize dronu za letu vs. vlek po vzletu (dron bez fyziky — nesmí zůstat kolizní tvar na vleku ani v kořeni scény), kolize s tahačem při zatáčení.
Ověř hmotnostní bilanci: součet `mass` dílů vs. `<base><mass>`/`<components>`, těžiště vs. osa kol (zátěž na oji; cíl 10–20 % hmotnosti u Car/Mini, <= 17 % u Max), plná nádrž ×2 u Max. Hledej díly s kolizí, které nemají být kolizní (kabely, hadice, štítky) a naopak.

#### P — parametry a vyváženost
Sestav tabulku **všech číselných parametrů** (XML vozidel, šablony, `Station.lua` konstanty, `Service.lua`, `Pad.lua`) pro Car/Mini/Max × S/M/L. Zkontroluj proti realitě (DJI Agras T25/T50/T100: nádrž 20/40/75 l, záběr, hmotnost, výdrž) a proti vanilla konvencím
(ceny a `dailyUpkeep` srovnatelných vanilla postřikovačů, `maxSpeed`, požadovaný výkon tahače, `lifetime`, `brand`, `typeDesc`).
Konkrétně:
1. **Dolet / dosah**: dnes platí jeden strop `maxRange` 1500 m a z baterie vychází 2,6–3,6 km, takže **všechny varianty mají stejný dosah**. Pavel: *menší drony mají mít menší dolet*. Navrhni vzorec/konstanty per varianta
   (a případně per vlek: Mini vs Max), vycházející z energie baterie, hmotnosti, rychlosti a rezervy na návrat + postřik; uveď výsledné dosahy v m a časy. Ověř vzorec v kódu (`Station.lua`/`Route.lua` — hledej `maxRange`, `getRange`).
2. **Nádrže**: dron (20/40/75 l) vs. hlavní nádrž vleku (Car 1000, Mini 450, Max 2×5000) vs. koncentrát a nafta; plní se v rozumném počtu cyklů? Max se dvěma dronem a 2 hadicemi: litry/min čerpadla, průtok při plnění obou.
3. **Baterie a čas**: výdrž × rychlost = dráha; plocha jedné dávky (l ÷ l/ha) vs. dolet; kolik dávek na baterii; nabíjení a nafta; Max `power#slots` 8 vs. počet baterií v konfiguraci (0–5 → u dvou dronů?).
4. **Ceny**: vlek + dron + baterie + kanystry vs. realita hry; ceny kanystrů a koncentrátu (viz DRON.md „Kanystr jako kupovaný objekt“).
5. Nesmysly: jednotky, nuly, rozpory mezi šablonou a vygenerovaným XML, parametry, které nic nedělají (mrtvé), hodnoty mimo rozsah v plánovači.
Výstup: tabulka „současně → navrženo → důvod“ + seznam změn, které vyžadují přestavbu modelu, a těch, které jsou jen XML/Lua.

#### L1 — revize Lua: Station, Drones, Fields, Service, Pad, Hotspot, Ladder, Sound, Debug, events
#### L2 — revize Lua: Route, gui/SprayDronePlannerScreen, Toolbox, Mixer + překlady použité v těchto souborech
Pro každý soubor: nil přístupy, chybné pořadí volání (`onLoad` vs `onPostLoad`), neuvolněné uzly/sample/efekty v `onDelete`, `registerFunction`/`overwrittenFunction` konzistence, listenery (`addActionEvent` — registrace i odregistrování,
`g_inputBinding`, kontextové `updateActionEventState`), konkurence `runAs`/`forEach` (únik kontextu dronu 2 do dronu 1, chyba uprostřed `runAs` nevrátí kontext — použít pcall/finally?), multiplayer (`streamWrite`/`streamRead`
musí si přesně odpovídat; `dirtyFlags`; klient × server rozlišení; události), savegame (klíče, zpětné načtení), výkon (alokace v `onUpdate`, raycasty za snímek), mrtvý kód, duplikace, magické konstanty, funkce > 150 řádků,
nepoužívané překlady a překlady chybějící (porovnej `g_i18n:getText(...)`/`$l10n_` klíče s `translation_cz.xml` a `_en.xml`).
Výstup rozděl: **A) skutečné chyby** (s opravou), **B) rizika**, **C) refactoring** (jen to, co se vyplatí; u každého co a proč, bez zbytečných abstrakcí). Dej pozor na rozdíly Car/Mini (`numDrones = 1`) vs. Max (2) — kód je společný.
Můžeš spustit `tools/lua_check.py`, `tools/audit_spec_fields.py`, `tools/test_split.py` (lupa) a napsat si vlastní lupa testy do `out\revize\<role>\` pro izolované funkce (dělení legů, výpočet dosahu, stav tlačítek).

#### X — XML / i3d / překlady / obchod / zapřažení
- `modDesc.xml`, tři XML vozidel, tři i3d, šablony: `tools/validate_mod.py`, kontrola odkazů na soubory/uzly (`tools/check_xml_nodes.py`), duplicitní/chybějící `index` cesty, `storeData` (obrázek, `rotation`, `brand`, `category`, `specs`, `functions`, `price`),
  `<license>`/verze, `<l10n>`, `inputBinding` — zda jsou všechny akce z kódu v modDesc a naopak, kolizní klávesy s vanilla (`Alt+1…9`, `C`, `X`, `U`), `<vehicleTypes>`/specializace/pořadí, sdílené materiály/textury (velikost v MB, chybějící `.dds`, mipmapy).
- **Zapřažení**: u každého vleku zjisti `attacherJoint` (typ, `jointType`) a porovnej s `inputAttacherJoint` strojů, za které se budou vozit (vanilla: pickup Lizard, traktory různých velikostí na Riverbend Springs, nákladní auta, ATV…). Sestav tabulku „vlek × tahač → drží?/výška oka/zalomení/hlášení hry“. Zjisti, jaký tahač Pavel ve hře reálně má
  (`E:\…\savegame11\vehicles.xml`, slot 11 je testovací kopie slotu 5), a které stroje mají stejný typ spojky. Co by bylo potřeba (např. druhý `attacherJoint` jiného typu), aby šel Max za velký traktor a Mini za ATV/malé auto.
- Výkon/brzdy/`maxSpeed`/`power`/`powerConsumer`: konformita s vanilla vleky (nájezdová brzda, 13pin, světla — viz Car).
- Překlady: úplnost cz × en, diakritika, zkratky klávesových akcí, délky textů v F1 panelu, jednotná terminologie (dron / vlek / přípravek / koncentrát).
- Log hry: pokud existuje `Documents\My Games\FarmingSimulator2025\log.txt` z minulého běhu, projdi varování a chyby týkající se módu.

#### Z — zvuk, efekty, světla, vzhled, HUD
Zjisti, **co hra nabízí zdarma** (vanilla vzorky zvuků `$data/sounds/...`, vanilla efekty `$data/shared/...`, vanilla světla/`realLights`, vanilla `dashboard` komponenty) a co by pro mód mělo smysl použít, aby se chování blížilo běžným herním mechanikám:
čerpadlo (plnění dronu, přečerpání), hadice, elektrocentrála (start/běh/vypnutí), nabíječka baterií, otevření bedny/víka/šachty, kanystr (sání/odložení), žebřík, rozkládání dronu a desky (servo), vrtule (výška podle rotoru S/M/L,
start, vzlet, přistání), postřik (hlas trysek, mlha — materiál, vítr), varování (nízká baterie, prázdná nádrž), tlačítka a jejich potvrzení, tlačítka v plánovači. Ke každému: dnešní stav v kódu, navrhovaný vanilla vzorek (cesta, jak se používá v jiné vanilla specializaci — dohledej příklad) nebo že se musí
dodat vlastní soubor (licence!). Prověř i: HUD a ukazatele naplnění, F1 nápovědu (délky textů, pořadí akcí, skryté akce), ikony (`store_*.dds`, ikony kláves, hotspoty na mapě, ikona v plánovači), obrázky obchodu (jsou prý zastaralé), světla (provozní, brzdová, obrysová, pracovní u vleku), nápisy a samolepky (decals) a
případné problémy s texturou (špatné UV, natažení, Z-fighting, chybějící specular/normal). Vizuální nálezy dokládej snímkem (`out\revize\Z\*.png`) jen tam, kde stačí `blender` render bez hry; **hru nespouštěj**.

### Fáze 2 — opravy (sériově podle vlastnictví souborů)

Řídící agent po přečtení reportů (a po rozhodnutí Pavla u věcí, které jsou jeho — viz níže) rozdělí nálezy do **pracovních balíků s disjunktním vlastnictvím souborů**; dva agenti nikdy neupravují tentýž soubor současně.
Orientační vlastnictví: (a) Lua jádro `Station`+`Drones`+`Fields`+`Service`+`Pad`; (b) Lua `Route`+`Planner`+`Toolbox`+`Mixer`; (c) modely Car; (d) modely Mini; (e) modely Max (build + export jsou 12 min a sdílí `.blend` → vždy jediný agent na vlek);
(f) překlady + modDesc + XML šablony; (g) zvuk/efekty. Opravy modelů: změna konstanty v `build_trailer_*.py` → `headless_*.py -- build render` → kontrola snímku → export na pozadí; po exportu ověřit `validate_mod.py`.
Každý balík končí: `lua_check.py` + `audit_spec_fields.py` + (pokud se týká) `test_split.py` zelené, zápis do `docs/DRON.md` (jen to, co čtenář potřebuje) a stručná zpráva (co změněno, jaké soubory, jak ověřit ve hře).

### Fáze 3 — testy ve hře (jediná instance hry → jeden agent, nebo řídící; **nikdy dvě sezení současně**)

Hra se spouští `tools/sdt_start.ps1 -SaveArgs "<volby prepare_testsave.py>"`, zastavuje `-Stop`. Kontrola po každém spuštění: `log.txt` bez `SprayDrone … Error` / `attempt to`. Matice (rozšiř podle Fáze 1, doplní X a P):

1. **Načtení a obchod**: každý ze tří vleků se načte bez chyb v logu; obchod: kategorie, název, cena, obrázek, ikona, specs, konfigurace Dron (bez/S/M/L) a Baterie; dílna: změna konfigurace.
2. **Zapřažení**: každý vlek za každý relevantní stroj (pickup, traktory různých velikostí, nákladní auto, ATV…): spojení, výška oka, zalomení při zatáčení, couvání, brzdy, stabilita při jízdě 40 km/h a rychlém brzdění, převrácení nezkoušet.
3. **Rozložení**: Car (žebřík), Mini (deska — rovinný terén, svah, překážka pod deskou, hadice nedosáhne), Max (dvě plošiny). Sklopení zpět. Hlášky a blokace.
4. **Všechny velikosti dronů** na každém vleku: vzlet, let nad polem, postřik (obě kapaliny), přistání, doplnění, výměna baterie, návrat. Dosah odpovídá navrženým hodnotám; mise přes hranici dosahu se odmítne.
5. **Max se dvěma drony**: dělení pole, dvě hadice, souběžné plnění, vzlet fronta, kamera `Alt+9`/`C`, dvojí návrat, pole hotové ohlásí jen poslední.
6. **Servis**: čerpadlo, hadice, bedna na kanystry (otevři/zavři, sání, odložení; Car 15 (3 nafta), Mini 4, Max 33 (9 nafta, 24 hlavních) slotů), naftový stojan, centrála, mixér a koncentrát, přečerpání do IBC, tankování na stanici.
7. **UI**: F1 panel, HUD ukazatele, hlášky, plánovač (mapa, nastavení, kreslení plochy, tlačítka), překlady cz/en (přepni jazyk), ikony kláves.
8. **Zvuk a světla** — zvuk se nesnímá, ověřuje se logem + (po dohodě) tím, že ho Pavel poslechne; světla v noci (`--time 22:00`).
9. **Uložení a načtení** (autosave uprostřed mise), pokračování mise.
10. Odolnost: nízká/vypnutá baterie, prázdná nádrž, vypnutá centrála, zhasnutý monitor, kurzor v menu, přepnutí na jiné vozidlo za letu, smazání vleku za letu (úniky uzlů).

Každý nález ze hry → oprava (opět v rámci vlastnictví souborů) → opakování scénáře. Snímky: `shot:`/`small:` z `fs25_input.ps1` (levné na tokeny, preferuj `small`).

## Rozhodnutí, která patří Pavlovi (neřešit sám, shromáždit a zeptat se najednou)

- Strop dosahu a vzorec dosahu per varianta (P) — pokud se výrazně liší od dnešního chování.
- Změny cen, nádrží a výdrží, které mění herní balanc.
- Cokoliv, co vyžaduje nový vlastní zvuk (licence) nebo přepracování modelu většího rozsahu.

## Co je „dotažené“

Žádná kolize modelů v obou polohách (kromě záměrných styků), žádný `Error`/`attempt to` v logu při celé matici Fáze 3, každý vlek jde za aspoň jeden běžný tahač a hra to přijme jako jinde,
číselné hodnoty jsou odůvodněné tabulkou (malý dron = menší dolet i nádrž), texty cz/en úplné, DRON.md odpovídá realitě, a `lua_check` + `audit_spec_fields` + `validate_mod` jsou zelené.
