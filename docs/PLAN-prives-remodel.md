# Plán: přemodelování přívěsu podle referenčního videa (nuWay Ag)

> **Stav k 2026-09-27 — tento dokument je překonaný, níže je historie.** Kolekce
> `SprayDroneTrailer_V2` popsaná dál v souboru nikdy nebyla (soubor obsahoval jen starý
> `SprayDroneTrailer` podél osy X, bez husího krku). Platí:
>
> - **Schválený vlek (Pavel, 2026-09-27):** `blender/build_trailer3.py` → kolekce
>   `SprayDroneTrailer3` ve `spraydrone_trailer_v3.blend`. Záloha schváleného stavu:
>   `blender/archiv/2026-09-27_v3_schvaleno/`.
> - Předloha nuWay „Spray Ready" gooseneck: 22 ft deckover + 32 ft letová plošina, schody
>   s otvorem v plošině, pilotní prostor se zábradlím nad husím krkem.
> - **Osa: čep vpředu na −Y** (jako vanilla vozidla po importu). Starý model byl podél X.
> - Podvozek srovnán s vanilla **Kingston Belvedere** (jediný gooseneck ve hře), importovaným
>   `blender-i3d-importer` do kolekce `REF_Belvedere` — jen reference, neexportovat.
> - Generátory jsou vedle schodů, ne pod nimi: pod strmým schodištěm (49°) není 0,8 m výšky.
> - **Menší verze za osobní auto, jeden dron** (2026-09-27, čeká na Pavlův názor):
>   `blender/build_trailer_car.py` → vlastní soubor `spraydrone_trailer_car.blend` (jména objektů
>   jsou v .blend globální a shodují se s velkou verzí). Podvozek podle vanilla **Stema Trius**
>   (`REF_StemaTrius`): tandem, r kola 0,30, rozteč 0,70, kulová spojka 0,50 m; paluba 4,2 × 2,1 m,
>   plošina 2,5 m, nádrž ~600 l. Skládací žebřík zezadu (schváleno 2026-09-27): uzly
>   `ladderSlide` → `ladderHinge` → díly; animace = vyklopit kolem X dozadu do vodorovné polohy,
>   pak zasunout o délku žebříku dopředu do kolébek pod plošinou. Náhled `set_ladder(t)` ve skriptu,
>   průběh ověřený bez kolizí ve 21 polohách.
> - Společné díly obou verzí jsou v `blender/sdt_parts.py`. Skripty se spouštějí
>   `exec(open(p).read(), {"__file__": p, "__name__": "__main__"})`.
> - **v0.2 (2026-09-27, ověřeno ve hře):** vlastní typ `FS25_SprayDroneTrailer.sprayDroneTrailer`
>   (`baseFillable` + `fillTriggerVehicle` + `enterable` + `sprayDroneStation`), nádrž 600 l
>   `liquidFertilizer`/`herbicide`, sdílená světla hry, opěrné kolečko (`moveSupport`), materiály
>   přepisuje `export_car_mod.py` na vehicleShader + detailLibrary, dron je v i3d pod `droneRoot`.
>   Nastoupit jde jen do rozloženého vleku (složený Tab přeskakuje), dokud je hráč uvnitř, nejde složit.
>   Pozor: vlastní specializace patří v modDesc do `<specializations>` (ne `vehicleSpecializations`).
>   Let dronu: zadání a stav v `docs/DRON.md`.
> - **Test ve hře prošel (2026-09-27):** slot 11 „SprayDrone test“ (kopie Riverbend ze slotu 5),
>   připravuje `tools/prepare_testsave.py`, spuštění `steam -applaunch 2300320 -autoStartSavegameId 11
>   -skipStartVideos -skipModUpdateDialog -cheats`, ovládání `tools/fs25_input.ps1`. Bez chyb v logu;
>   zapřažení na kouli, kola, 300 l vody, skládání žebříku oběma směry i jízda fungují.
>   Pozor: animace foldable má čas 0 = rozloženo, 1 = složeno (FS25 Foldable.lua).
> - **Mód `FS25_SprayDroneTrailer` v0.1 (2026-09-27):** `mod/FS25_SprayDroneTrailer/`,
>   do hry propojený junction z `E:\SteamLibrary\FS25-Mods\`. Sestavení: v Blenderu nejdřív
>   `build_trailer_car.py`, **v dalším samostatném volání** znovu načíst soubor a pak `export_car_mod.py`
>   (stavba + export v jednom volání shodila Blender v `_ctypes` — exportér sahal na data smazaných objektů).
>   Kontrola: `python tools/validate_mod.py` (vehicle.xsd a modDesc.xsd ze hry). Typ `waterTrailer`,
>   vzor ABI Water Trailer 550: kolizní komponenta jako kořen, kola generovaná hrou (195_50R13 + ráfek Stema),
>   i3dMappings počítané z hotového i3d (exportérův „Update XML“ bere celou scénu → špatná čísla).
>   Zatím chybí: funkční světla, textury/vehicleShader, dron jako součást, animace opěrného kolečka.

Zdroj: https://www.youtube.com/watch?v=wpi7OzPzrWc (staženo do `reference/video/trailer_ref.mp4`,
kontaktní listy v `reference/contact_sheets/`, vybrané detailní snímky v `reference/frames_hq/`).

Drony (`build_drone.py`) zůstávají beze změny, jen se přemístí na nový přívěs.

## Identifikované díly z videa

1. Rám (22ft deckover), tandemové 8K nápravy, 16-ply pneumatiky, rezerva pod rámem
2. Podlaha ze dvou úrovní — nižší přední deckover najetí + vyšší zadní "flight deck"
   (kompozitní, protiskluzová)
3. Sloupková konstrukce stříšky + rohové trojúhelníkové výztuhy ("gusset") s logem nuWayAg
4. Stříška s panelem zvukové izolace ("sound proofing") pod plechem
5. Schodiště vzadu — skládací, diamantový plech na schodech (aktuální model upravit podle referencí)
6. Zábradlí kolem plošiny + síťová "pilot protection wall" se skládací brankou vpředu
7. Nádrže: 175gal indukční nádrž (kónický tvar, 2" plumbing) + 50gal čirá nádrž na vodu,
   společný "easy manifold" s uzávěry
8. Dva hadicové navijáky na sloupech stříšky (30ft chemická, 50ft vodní hadice)
9. Dva generátory (Predator/Duromax D12000iE) vzadu na plošině
10. Toolbox pod rámem + elektrická rozvodná skříň
11. Uzamykatelný bezpečnostní box na dron (diamantový plech, výklopné víko) — doplněk
12. Hydraulický zvedák (standard) + volitelný 4bodový hydraulický vyrovnávací systém (rohové nohy)
13. Světla — brzdová/couvací vzadu, pracovní světlo, červený výstražný LED pás
14. Dron na plošině — použít existující `build_drone.py`, jen upravit pozice/rotace

## Postup (malé kroky, vždy screenshot + kontrola)

Pro každý celek: nejprve samostatný model bokem (vlastní kolekce/offset stranou od scény kvůli
prohlížení), pak instance/verze zakomponovaná do sestavy přívěsu na správné pozici.

- [ ] Fáze 0 — rozbor videa, seznam dílů (tento dokument) ✅
- [x] Fáze 1 — rám, nápravy, kola, rezerva (bumper-pull A-rám, tandem, rezerva na boku u oje)
- [x] Fáze 2 — dvouúrovňová podlaha/deck (nízká spodní paluba je součástí rámu z fáze 1)
- [x] Fáze 3 — sloupky + rohové gussety + STŘECHA (⚠️ oprava konceptu: NENÍ to zvýšená plošina pro
      dron, je to jen stínící střecha na sloupcích nad nízkou palubou z fáze 1 — hlavní servisní
      vlek je jednoúrovňový, nádrže/generátor/dron stojí na stejné nízké palubě; dvouúrovňová
      zvýšená "flight deck" plošina patří k JINÉMU produktu "standalone drone trailer", ten
      nestavíme)
- [x] Fáze 4 — schodiště k malé vyvýšené "pilotní" plošince u střechy vzadu (odtud pilot řídí dron
      přes střechu vleku) + síťová "pilot protection wall" kolem ní. Plošinka je záměrně KANOTUJE
      MIMO střechu (za její zadní hranou), jinak by zábradlí kolidovalo se střechou nad sebou.
- [x] Fáze 5 — nádrže (175gal indukční s kuželovým dnem + 50gal čirá) + manifold s ventily +
      2 hadicové navijáky na sloupcích střechy — na nízké palubě, mimo trasu schodů
- [x] Fáze 6 — 2× generátor, toolbox u oje, uzamykatelný bezpečnostní box na dron — na nízké
      palubě, mimo trasu schodů (ověřeno numericky bez kolizí)
- [x] Fáze 7 — hydraulický zvedák vpředu u oje + 2 rohové vyrovnávací nohy vzadu (vysunuté až na
      zem), pracovní světlo pod střechou
- [x] Fáze 8 — drony z `build_drone.py` (beze změny) napojené na nízkou palubu novým helperem
      `build_drones_on_deck()` v `build_trailer2.py`; celková kontrola bez kolizí/propadu pod zem

## Stav: kostra hotová (fáze 1–8)

Nový model je kompletní v `SprayDroneTrailer_V2` (+ drony v `SprayDrone`), vedle starého modelu
pro srovnání. Numericky ověřeno bez kolizí (Z rozsah 0–3,465 m, délka ~8,9 m s ojí).

### Oprava podle čerstvé reference (snímek "11% TONGUE WEIGHT")

- Pilotní plošinka přesunuta z (chybně) zadní hrany na **přední** hranu střechy, blízko oje —
  podle referencního profilu vleku za jízdy. Schody teď vedou od nízké paluby dopředu nahoru.
- Oj zjednodušena z dvou sbíhavých nosníků na **jeden rovný centrální nosník** (bumper-pull).
- Starý model (`SprayDroneTrailer`, `build_trailer.py`) smazán ze scény, nový `SprayDroneTrailer_V2`
  je teď na středu (offset 0).

### Druhé kolo oprav podle dalších referenčních záběrů

- Plošinka přestala být samostatný vyčnělý box — je to teď **přední část střechy** (FlightDeck)
  přes celou šířku, jen s obvodovým zábradlím a sítí (nic dalšího tam nebylo potřeba stavět)
- `PLATFORM_WIDTH` zúžena zpět na `DECK_WIDTH + 0.08` — sloupky teď sedí na hraně rámu, ne mimo něj
- Schody přepracovány ze svislého žebříku na **strmé schodiště se stupni a schodnicemi**
  (`build_front_stairs`), mimo půdorys paluby, u předního rohu
- Drony přesunuty ze spodní paluby **na střechu** (`PLATFORM_Z`) — tam se podle videa reálně létá,
  přístup po schodech + plošince
- Rezerva u oje odstraněna (na referencích není vidět, matlala pohled)
- Generátor obarven podle skutečnosti — zjištěno webovým hledáním, že "D12000iE" NENÍ generický
  generátor, ale oficiální **DJI Agras multifunkční generátor/nabíječka baterií** (oranžová skříň
  v černé kleci, 30L nádrž, 1500W AC výstup) — barva opravena, tvar zůstává zjednodušený box
- Zjištěno (websearch): nuWay Ag oficiálně uvádí nádrže 1000gal hlavní + 175gal indukční + 50gal
  na vodu (ne jen 175+50 jak jsem odhadl)
- Tvar nádrží přepracován: 1000gal hlavní je teď kapslovitý válec (`add_capsule_x`, zaoblené konce
  místo kónického dna), 175gal indukční je hranatá tote nádoba s černými popruhy, 50gal na vodu je
  malá kapsle — přeuspořádáno na nízké palubě bez kolizí

### Co ještě zbývá (další kolo, ne kritické pro funkční tvar)

- Přesné "bokem" ukázkové verze detailnějších dílů (bezpečnostní box, generátor) pro lepší
  prohlížení — u primitivních dílů (nádrže, generátory) asi netřeba, zvážit jen u složitějších
  sestav
- Jemné doladění proporcí podle `reference/frames_hq` (přesnější tvar nádrží, mřížka gussetů,
  diamantový plech na schodech/palubě jako textura/materiál)
- Nahradit starý `build_trailer.py`/kolekci `SprayDroneTrailer` tímto novým modelem, až bude
  Pavel s výsledkem spokojený (zatím schválně ponechány vedle sebe pro srovnání)
- Export do GIANTS i3d (i3d exportér zatím nenainstalovaný)

Generátor skriptů zůstává v `build_trailer.py` (idempotentní, parametrický), nové díly se přidávají
jako další funkce volané z `build()`.
