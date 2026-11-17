# Prompt: oprava modelu malého vleku (Mini) — 2026-10-11

Zadání pro agenta, který chyby nejdřív **analyzuje v kódu a v modelu**, pak je **opraví** a výsledek **ověří
na renderech**. Zdroj: Pavlovy snímky z hry (4 ks) a jeho slovní popis. Řeší se **jen malý vlek (Mini)**.
Car a Max se nesmí rozbít (sdílené moduly `sdt_*.py`, `SprayDronePad.lua`, `SprayDroneToolbox.lua`,
`SprayDroneStation.lua` jsou společné — každá změna v nich musí zůstat neškodná pro ostatní vleky).

## Kontext

- Projekt: `E:\ClaudeProjects\FS25-SprayDrone`. Mod `mod/FS25_SprayDroneTrailer/`, modely se staví skriptem
  v Blenderu: `blender/build_trailer_mini.py` (staví), `blender/headless_mini.py -- build|render|export`
  (bez okna), `blender/export_mini_mod.py` (export do i3d + XML), `blender/make_folded_variant.py`
  (složená varianta), šablona `blender/templates/sprayDroneTrailerMini.xml.in`.
  Čti `docs/DRON.md` (sekce Stav, Na příště, Úpravy z 2026-10-05 až 10-07) a `docs/PLAN-koncentrat.md`.
- Blender: `blender.exe -b --python blender\headless_mini.py -- build` (cesta k `blender.exe` je v dřívějších
  příkazech / dokumentaci; když ji nenajdeš, vyhledej instalaci Blenderu mimo disk `V:`).
- Pravidla: odpovídej česky; soubory (náhledy, mezivýstupy) jen v projektu (`tmp/mini/`, `out/`); **žádný commit**
  ani push; **hru nespouštěj** (testuje Pavel); disk `V:` je zakázaný; žádné zbytečné komentáře v kódu;
  zpětná kompatibilita se neřeší; vanilla herní mechaniky mají přednost před vlastními (viz `PLAN.md`).
- Pracovní strom je špinavý (necommitnuté změny ze sloučení nafty do bedny) — to je výchozí stav, nic nevracej.
- Plány a stavové dokumenty ber s rezervou, ověř je proti skutečnému kódu a modelu.

## Postup

1. **Analýza.** Pro každý bod níž najdi příčinu: konstanta / funkce v `build_trailer_mini.py`, uzel v i3d,
   kus Lua nebo XML. Udělej Workbench render stávajícího stavu (`headless_mini.py -- render`) a **prohlédni
   obrázky**, ať víš, co Pavel vidí. Výsledek analýzy shrň do tabulky (bod → příčina → navržená oprava) a
   ulož do `tmp/mini/analyza.md`. Neptej se Pavla, pokud to jde rozhodnout ze zadání nebo ze sousedního kódu.
2. **Fáze A — složený stav (nejdřív tohle).** Body A1–A6. Po fázi: build, render ze 4+ stran, kontrola
   snímků, export, `tools/validate_mod.py`, `tools/lua_check.py`.
3. **Fáze B — rozkládání a plnění.** Body B1–B7. Totéž.
4. **Zápis.** Stručně do `docs/DRON.md` (sekce Stav / Na příště): co se změnilo, co zůstává neověřeno ve hře.
   `STAV`-style přepis, ne přidávání historie.

## Fáze A — složený stav

**A1. Přistávací plocha / bedna není přes celou šířku vleku.** Složená bedna (deska s diamantovým plechem,
`CRATE_HX = 0,769`, tj. 1,54 m) je užší než vlek (`BASE_W = 1,86`) — vlevo i vpravo zůstává mezera a vidět
dřevěná paluba. Má jít od okraje k okraji vleku (po rozložení také celá šířka plošiny). Zkontroluj, co na šířce
závisí: panely `_crate_panel`, nožičky `_crate_leg`, plachty `build_pad_tarps`, kolize, pozice dronu, hranice
volného prostoru (`CRATE_CHECK_HEIGHT`), šířka rozložené plošiny.

**A2. Víko šachty baterií se ve složeném stavu otevírá špatně.** V rozloženém stavu je směr odklopení správný,
ve složeném ne. Víko se má odklápět **jedním směrem — k centrále** (závěs na straně od centrály, víko se
zvedá a sklápí směrem k ní), a to stejně v obou stavech. Příčina bude v `build_bay_lid` / `BAY_LID_BASIS` /
`BAY_ROTATE_MATRIX` / `_transform_new` (šachta se po sloučení nafty přesunula za generátor a otočila o 90°)
a v tom, jak `make_folded_variant.py` a export variantu skládají. Oprav osu, pivot a animační klíče
(`BAY_LID_OPEN_DEG`, `LID_TIME`) tak, aby byly shodné; ověř render obou variant v otevřené poloze víka.

**A3. Bedny na kanystry jsou nalepené na nádrž; mají být na kraji vleku.** Na jedné straně už u kraje je
(`BOX_X = -0,865…-0,545`), na druhé ne (`BOX2_X = STRIP_X = 0,40…0,72` — u nádrže). Obě patří úplně ke krajnímu
lemu paluby, symetricky. Dej pozor na: sloty/`canister_offset`, uzly kanystrů a jejich aktivace v
`SprayDroneToolbox.lua` (pozice se čtou z uzlů — ověř, že se nerozbijí), šachta baterií a kabel nabíječky
(`build_charger_cable`) nesmí kolidovat.

**A4. Hlavní nádrž je zbytečně vysoká a má víčko na boku.** Nádrž (450 l, `build_pad_tank`) udělej **nižší**
(klidně plošší a širší), plnicí uzávěr patří **nahoru**, ne na bok. Prostor, který uvolní posun beden ke krajům
(A3), nádrž vyplní do šířky — objem musí zůstat 450 l (sedí s `PAD_LITERS`, geometrie ↔ kapacita; spočti
objem z rozměrů). Nádrž přestavěj celou (viz B6 — popisky a hadice kolem ní).

**A5. Kola jsou obří.** Mini má `TIRE_DIMENSIONS = "425_55R17"`, `WHEEL_R ≈ 0,45` — to je kolo traktoru.
Malý vlek má mít malá kola jako podobné přívěsy. Podívej se, **z kterého vleku Mini vychází** (Car,
`build_trailer_car.py`: `320_60R12`, `WHEEL_R = 0,354`, `WHEEL_W = 0,32`, rozchod/rozteč a pružiny) a převezmi
od něj kola, blatníky, pružiny, napojení na osu. Přepočítej všechno, co na poloměru visí: výška paluby
(`DECK_TOP`), osa v XML (`wheels`, `tireType`/rozměry, `physics` — poloměr a šířka kola), `AXLE_Y`,
`CENTER_OF_MASS`, kolize, vzdálenost kola od krajní bedny a od nádrže, krabice kol (arches). Nic nesmí
procházet palubou ani kolem.

**A6. Kontrola.** Složený vlek ze 4 stran + shora: žádné mezery, nic neprochází, hmotnostní rozložení
(zatížení oje 10–20 %, `HITCH_LOAD`).

## Fáze B — rozkládání, plnění, koncentrát

**B1. Dron při rozkládání vyletí z bedny nahoru — chyba.** Správné pořadí: (1) bedna se rozloží tak, aby
panely **neprocházely dronem** (dron zůstane stát na své ložné ploše, panely se vyklopí kolem něj), (2) teprve
po úplném rozložení se dron **otočí o 90° a posune** na vzniklou přistávací plochu. Dnes se dron zvedá do
`CRATE_LIFT = 1,15 m` a ruší se kolize. Najdi, kde se to dělá (animační klipy `foldTrailer`, `DRONE_UNFOLD_TIME`,
`DRONE_EXTRA_ROT`, `CRATE_SETTLE` a Lua v `SprayDronePad.lua` / `SprayDroneStation.lua`), a přepracuj
sekvenci. Skládání zpět = obrácený sled (dron se nejdřív přesune a otočí zpět, pak se bedna složí). Časy v
animaci (`FOLD_DURATION`, `LID_TIME`, `CLAMP_TIME`, `CABLE_TIME`) přeuspořádej konzistentně. Zkus posloupnost
vykreslit v 6–8 mezi­snímcích animace a **kontroluj průnik panelů s dronem**.

**B2. „Místo pro plnění dronů" visí ve vzduchu.** Plnicí hrdlo (`DRONE_FILL_PORT`, oranžový kroužek nad
plošinou) se při přesunu dronu nepohybuje s ním a zůstává na pozici, kde bylo. Má být **pevnou součástí
dronu** (potomek jeho uzlu), po celou dobu ve stejné orientaci vůči dronu, a při letu/přesunu jít s ním.

**B3. Na přistávací ploše chybí namalované H.** Doplň heliportové „H" (kontrastní barva, přes střed plošiny,
vyrovnané s osou, ne pod dronem skryté — ať je vidět i s dronem; zvaž velikost vůči rozměru dronu S).
Zkontroluj existující `build_decals` / `pad_label_geometry` / texturu `sdt_vmask_trailer` — dřívější záznamy
tvrdí, že tam H je; ověř na renderu, že skutečně je a viditelné.

**B4. Orientace dronu při plnění.** Po přesunu na plošinu otoč dron tak, aby **nádržka (plnicí hrdlo) mířila
k hadici**, a animace plnění (hadice → hrdlo) nešla skrz tělo dronu. Hadice se přitom nesmí zlomit
(viz B5).

**B5. Hadice je zlomená.** Dráha plnicí hadice (`HOSE_START`, `HOSE_LAY`, `HOSE_PARK_TIP`,
`HOSE_PARK_DIR`, `tune_mini_hose.py`) dělá prudký zlom. Má být **mírně klikatější, plynulá křivka** bez ostrých
úhlů (min. poloměr ohybu úměrný průměru hadice), vždy nad palubou a mimo nádrž (viz B6). Sleduj i pozici
koncovky vzhledem k dronu po B4.

**B6. Nádrž — přepracovat celou.** (Navazuje na A4.) Popisky: dnes je jeden uprostřed, druhý na kraji
(`pad_label_geometry`, `sdt_labels.py`) — nech **jeden jednotný systém popisků** (např. objem + výstražný štítek)
na jednom logickém místě na bočnici viditelné z boku; nic nepřesahuje hranu. Hadice a potrubí
(`build_mini_plumbing`, hadice z čerpadla) **nesmí procházet nádrží** — veď je kolem nebo pod/ vedle ní,
koncovky na skutečných výpustech/hrdlech. Zkontroluj kolizní tělesa nádrže.

**B7. Koncentrát je samostatný druh plniva.** Ve HUD i v kódu je u induktoru/mixéru „Herbicid", ale jde o
**koncentrovaný herbicid** (v mixéru se ředí vodou). Má to být **vlastní fillType** (ne vanilla `HERBICIDE`),
s vlastním názvem (cs/en l10n), ikonou, cenou/hustotou a vazbou na kanystry s koncentrátem a na míchání
(`SprayDroneMixer.lua`, `modDesc.xml`/`fillTypes`, `sprayDroneTrailerMini.xml`, `l10n`). Hotový postřikový
roztok pro dron zůstává mix ředěný (zkontroluj, co dron skutečně nese — nesmí se rozbít stávající výpočet dávek
a `PLAN-koncentrat.md`). Vanilla mechaniky (FillUnit, FillType API) mají přednost před vlastními; zjisti, jak
nové plnivo ve FS25 správně zaregistrovat (viz `fs25-modding` skill a `giantsDocu/`). Ověř, že kanystry/nalévání
z ruky do koncentrátu (ObjectStorageDialog) dál fungují. Ve hře to otestuje Pavel — označ v zápisu, co je
neověřené.

## Hotovo, když

- Všech 13 bodů je buď opraveno a ověřeno na renderech (cesty k obrázkům v `tmp/mini/`), nebo je výslovně
  napsáno, proč ne a co potřebuje rozhodnutí Pavla.
- `blender/headless_mini.py -- build` a `-- export` proběhnou, `tools/validate_mod.py` a `tools/lua_check.py`
  jsou čisté (kromě dříve známé nesouvisející chyby Car XSD).
- Car a Max se dál přestaví/exportují stejně (rychlý build kontrola) — sdílený kód jsi nerozbil.
- Zápis v `docs/DRON.md` je přepsaný, ne nalepený. Žádný commit.
- Závěrečná zpráva: tabulka bodů (stav), co nejvíc rizikové k testu ve hře, otevřené otázky.
