# Vzhled malého vleku (po 0.9.0.0) — stav

## Stav (2026-09-28 19:15, přerušeno na Pavlův pokyn „stop“)

Zadání (Pavel odsouhlasil): 1) lepší materiály z vanilla `detailLibrary` (slzičkový plech na desku, karbon na
ramena/listy, guma, plast), 2) špína a opotřebení (UV pro vanilla `Washable`/`Wearable`), 3) nápisy a nálepky
v jednom vlastním atlasu (štítky baterií S/M/L, displej nabíječky, výstražné pruhy, nápis na dronu, bez log DJI),
4) nový obrázek do obchodu a ikona, 5) konec oje: kulová hlava s nájezdovou brzdou, ruční brzda, pojistné lanko,
zásuvka 13pin (poloha `attacherJoint`, kolize a opěrné kolečko beze změny).

Kam subagent došel (podle souborů, závěrečnou zprávu nenapsal):
- Změněno: `blender/build_trailer_car.py`, `sdt_parts.py`, `export_car_mod.py`, nový `blender/decal_layout.py`,
  `blender/textures/sdt_decals.png`, `.blend` (19:04), export do modu 19:11 (i3d, shapes, xml, `store_*.dds`,
  `icon_*.dds`) a nové textury `vehicles/sprayDroneTrailerCar/textures/sdt_decals.dds`, `sdt_vmask_trailer.dds`,
  `sdt_vmask_drone.dds`.
- Byl v herním testu (hra spuštěná 19:13, snímky `out/mod_build/tx_*`): špína a opotřebení na vleku fungují
  (`tx_dirt_L.png`), nápisy „Spray Drone Service“ a nálepky jsou vidět, oj zapřažená `tx_coupler_hitched.png`.
  V logu žádné chyby modu. Náhledy z Blenderu `tx_pv_*.png`.
- Poslední krok před stopem: předělával `capture_view` / `make_images` v `export_car_mod.py` na render (obrázek do
  obchodu) — **může být rozpracovaný**, před dalším exportem zkontrolovat, že `export_car_mod.py` projde.
- Nejisté: jestli je hotová koncovka oje (bod 5) celá, a jestli bod 3 (atlas) je úplný. Ověřit proti snímkům
  `tx_pv_coupler*.png`, `tx_pv_charger.png`, `tx_pv_drone.png`.
- `docs/DRON.md` k vzhledu neaktualizovaný. Záloha před tímto kolem **není** (poslední: `out/plan09/b3_tmp/car_before_b3.blend`
  a `blender/archiv/2026-09-28_pred_0.8/`).

## Opravy 2026-09-29 (Pavel: hadice skrz dron, baterie trčí, trubky ve vzduchu)

- Baterie v dronu leží v šachtě v barvě trupu (`<prefix>BatteryBayWall*`), vidět je jen víko; zásuvka na hřbetu zmizela.
  Šachta pořád vystupuje ~13 cm nad trup (baterie 0,37 × 0,23 × 0,13 se do trupu M nevejde kvůli GPS věži a kloubům).
- Výměna baterie je animovaná (`startBatteryMove` / `updateBatteryMove` v `SprayDroneService.lua`): vybitá obloukem
  z dronu do nabíječky, pak nabitá z nabíječky do dronu, `BATTERY_MOVE_TIME` 1,4 s na kus. Ověřeno ve hře (fx_1*).
- Navíječ přesunutý dopředu vpravo pod palubu (`REEL` y −1,78), hadice leží vpředu na desce mezi heliportem a
  nabíječkou, k hrdlu jde přes `hoseVia` (atribut `<drone>`, přední hrana trupu nad nosem), koncovka stoupá o
  `HOSE_LIFT` a do hrdla sjíždí shora (`HOSE_PORT_APPROACH`). Klidová délka 3,27 m.
- Rozvod (`build_plumbing`): výpust hlavní nádrže vpředu dole + výpust indukční nádrže → T-kus → sání čerpadla,
  výtlak čerpadla → otočná spojka navíječe. `HoseReel_0_TankPipe`, `Tank_Main_HoseFitting` zmizely.
- Ve hře neověřeno: nová poloha navíječe a hadice (export 2026-09-29 prošel, offline testy zelené).

Pokračování: projít snímky tx_*, zkontrolovat `export_car_mod.py` a export headless, `tools/lua_check.py`,
`tools/validate_mod.py`, doplnit chybějící body, jeden krátký test ve hře, DRON.md.

## Truhla nabíječky (2026-09-29, Pavel)

- Nabíječka je trvale ve truhle na horní palubě vpředu vlevo (`Chest_*`, tmavá barva `SDT_PaintDark`); buňky nabíječky
  posunuté (`CHARGER_CELL_X/Y`), aby truhla nepřesáhla okraj plošiny. Víko `chargerLid` má závěs na přední hraně,
  v i3d je otevřené (rozložený vlek, 92°), zásuvka je na levé vnější stěně.
- Kabel `chargerCable` je jediný uzel se zástrčkami na obou koncích jako dětmi (`Charger_Plug`, `Gen_0_ChargePlug`),
  v animaci `foldLadder` se skryje viditelností (0–0,05 s); víko se zavírá 0,2–1 s. Rozkládání jde stejnou animací zpět.
- Zadní bedna dole (`Toolbox`) zůstává prázdná a bez víka: později na koncentrát hnojiva k míchání na místě.
- Ve hře neověřeno.

## Drony a baterie podle DJI (2026-09-29, Pavel)

- Modely S, M, L (T25, T50, T100) a baterie přepsané podle oficiálních fotek DJI (`reference/drone/`, specifikace z
  ag.dji.com): fasetovaný šedý trup, radar, bílá nádrž, štíhlá ramena se skládacím kloubem, souosé gondoly,
  A-nohy. Popis v `docs/DRON.md` (sekce Vzhled dronů). Záloha původní podoby: `blender/archiv/2026-09-29_drony_pred_DJI/`.
- Uzly pro skript, rozměry, lyžiny a poloha lůžka baterie zůstaly; plnicí hrdlo se přesunulo vedle baterie.
- Obrázek do obchodu se teď kreslí se zavřeným víkem truhly a skrytým kabelem.
- Ve hře neověřeno (export prošel, offline validace jako dřív).
- Postřik přepsaný na vlastní částicovou mlhu (kužel od trysek k zemi, `blender/build_spray_mist.py`, `effects/sprayMist.i3d`);
  ověřeno ve hře v ladicí smyčce `DEBUG_FORCE_MIST`. Detail v `docs/DRON.md` (Efekt postřiku).

## Osm bodů 2026-09-29 (Pavel)

Hadice mimo dron, Obnovit pole, baterie letí do truhly před zavřením víka (držák dole zrušen), bez popruhů, složení z vleku
bez motoru, rozložený vlek stojí, barvy vrtulí a proužků v obchodě, kulatější hadice. Popis a co je ověřené ve hře:
`docs/DRON.md` (Úpravy 2026-09-29).


## Kolo 2026-09-29 večer (Pavel: nádrž dronu, koncovka, spodní paluba, mlha, ladění)

Nádrž dronu měla obrácené normály (`Mesh.loft`, opraveno), koncovka hadice jako pistole z benzinky (`sdt_nozzle.py`), agregát
(`sdt_generator.py`, výfuk dopředu, panel, víčko nafty), nádrže / čerpadlo / potrubí / bedna (`sdt_tanks.py`), mlha o 20 % řidší,
fosforeskující žlutá a oranžová (`glow`), ladění za běhu (`SprayDroneDebug.lua`, `tools/sdt_debug.ps1`, viz DRON.md).
Ve hře ověřeno: reset dokončeného pole (`coverField`), agregát / nádrže / bedna / koncovka v klidu, řidší mlha. Neověřeno: kouř z nového
výfuku, plnění nafty s novým kvádrem, barvy vrtulí v obchodě, koncovka v hrdle dronu při přečerpávání. Nálepky na nádržích, čerpadle a
bedně nejsou (přání agenta: štítky 600 l / 100 l, stupnice, výrobní štítek čerpadla, značky na bedně).

## Koncentrát, mixér, bedna, zvuky, velikosti nádrže (2026-09-30)

Zadání a kontrakty: `docs/PLAN-koncentrat.md`. Hotovo (sestaveno a exportováno, 840 uzlů): 4 velikosti hlavní nádrže s polepkami
(`sdt_bigtank.py`, objectChange v konfiguraci nádrže), koncentrátová nádrž (fill unit 3) s hrdlem, mixér místo T-kusu (`sdt_mixer.py`),
dutá bedna s víkem a 4 kanystry (`toolboxLid`, `toolboxCanister1..4`), polepky (`sdt_labels.py`), míchání při plnění dronu
(`SprayDroneMixer.lua`), kanystry a jejich akce (`SprayDroneToolbox.lua`, Alt+Z/X/C/V/B), zvuky (`SprayDroneSound.lua`).
Ve hře ověřeno jen načtení modu (vlek, konfigurace, i3d) bez chyb v logu. Neověřeno: vzhled nových dílů, objectChange nádrží,
míchání a plnění dronu, zvuky, aktivace a animace bedny, kanystry, uložení a multiplayer.
Testovací save: `tools/prepare_testsave.py ... --tank 300|800|1000|1500 --water 500 --concentrate 40`.

Ověřeno ve hře 2026-09-30 (rychlost x3): vlek se načte bez chyb; bedna se otevře (R), HUD se sloty, kanystry se naplní (`toolboxFill`) a
Alt+C vyleje kanystr do koncentrátové nádrže; plánovač ukazuje míchání a dostupné litry; dron se plní s mícháním (voda 500 → 473 l,
koncentrát 50 → 41 l, poměr ≈ 25 %); konfigurace nádrže 300 l zobrazí malou nádrž s polepkou 300 L. Stále neověřeno: zvuky,
vypuštění nádrže do kanystru, plnění kanystru z palety, 800 a 1500 l vizuálně, kouř z výfuku, multiplayer.
Okno hry do popředí při dlouhém nečinném PC: nejdřív stisk Alt (keybd_event 0x12) a SetForegroundWindow.
