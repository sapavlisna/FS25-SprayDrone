# Kontrola vstupních/výstupních bodů a zákrytu světel (2026-10-29)

Jen kontrola, nic v modu se neměnilo. Zdroj pravdy je **exportovaný i3d** (ne .blend): scéna se staví
`blender_i3d_importer`em bez korekce os a transformace všech uzlů se přepočítají z XML i3d (Euler XYZ, R = Rz·Ry·Rx,
ověřeno na směru světel: zadní svítí −Z, boční ±X). Rámec i3d: X vlevo, Y nahoru, Z dopředu, země y = 0.

- Rozložené Mini = přesně `SprayDronePad.applyPose(plan, deploy = 1)` na rovině: čepy Z/H/P 0°, boční stěny vyklopené
  o `acos((0,012 − 0,7325)/0,819)` = **151,6°**, nožičky 0,695 m, carrier na středu plošiny (endOffset −3,036 m),
  dron rozložený (`foldPart unfoldedRot`), víko šachty 100°. Middle/Max: animace `foldLadder` v čase 0 / na konci.
- Světla: vanilla `lizard/rearLight52`, `sideMarker05`, `plateNumberLight03` naimportované z dat hry a připojené jako
  `SharedLight` (`link(linkNode, rootNode)`, root si drží svou lokální transformaci). Viditelnost = paprsky
  z pozorovatelů 10 m od světla (úhly −45…45°, výšky oka 0,5 / 1,0 / 1,5 / 2,5 m) na 9 bodů skla.
  SPZ jako obdélník 0,30 × 0,20 m na `licensePlateBack`.
- Body: poloha, nejbližší povrch (BVH), „uvnitř“ (hlasy 14 paprsků zevnitř), osy uzlu, vzdálenost od obrysu,
  volno nad bodem; dosah pěšky = 3D vzdálenost od **nohou** hráče (`Player:getPosition` vrací chodidla) stojícího
  0,3 m za obrysem.

Skripty a výstupy: `out/check_body/scripts/` (`analyze.py <klíč> [render]`, `mini_detail.py`, `reflectors.py`,
`mill_bag.py`), surová data `out/check_body/report_*.json`, `reflectors_*.json`, obrázky `out/check_body/*.png`.

## 1. Světla, SPZ, odrazky

| vozidlo | stav | zadní světla | boční obrysky | SPZ | odrazky |
|---|---|---|---|---|---|
| Mini | složeno | 100 % | 100 % | 100 % | OK |
| **Mini** | **rozloženo** | **48 %; zezadu ve výšce oka ≥ 1 m 0 %**; pouzdra zařezaná 12 mm do `Crate_PanelZ` | viditelné, ale **pouzdra prochází sklopenými stěnami** | **49 %; z ≥ 1,5 m 0 %** | zadní 70 % (z ≥ 1,5 m 0 %), **boční L2/L3, R2/R3 0 %** |
| Middle | složeno | 100 % | 100 % | 100 % | **přední L/R 66 %** (spodní roleta `tarpFrontRoll` y 0,60 visí před nimi) |
| Middle | rozloženo | 100 % | 100 % | 100 % | OK (SideR0 88 % za žebříkem) |
| Max | oba | 100 % | 100 % | 99 % (tažné zařízení) | `Underrun_Reflector0/1` 59 % (za `Max_RearHitch` a držákem SPZ, oba stavy) |

Žebřík Max (rozložený vpravo u z −1,75) ani Middle obrysky nezakrývá. Pravé `rearLight52_right` se jen zdálo,
že vězí v nosníku — po započtení posunu kořene (0,029 m) je čisté.

### Mini rozložené — proč to zakrývá

- Plošina (`Crate_PanelZ/H/P`) leží ve výšce kotvy 0,72 m (spodek **0,676 m**) od z −1,40 do **−4,44 m**, šířka ±0,93 m,
  tedy přes celou zadní stranu. Zadní světla mají střed 0,62 m, vršek pouzdra **0,688 m** → vršek o 12 mm zasahuje
  do panelu Z; rovně dozadu stojí 0,70 m za sklem noha `Crate_LegSleeve2`. Paprsek od světla k oku ve výšce 1 m na 10 m
  vystoupá za 3 m délky plošiny nad 0,676 → **snižování světel nepomůže** (ani o 15 cm).
- Boční stěny po sklopení: x 0,93…1,325, y 0,01…0,74, z −1,384…−0,07. Obryska `sideMarker05` (x 0,933…1,060,
  y 0,58…0,68, z −1,30…−1,26) trčí 12,5 cm do boku přímo pod čepem → stěna jí prochází (sklo zůstane venku, proto
  „viditelná“). Odrazky SideL2/L3 (z −0,25, −1,10, y 0,50) jsou pod stěnou úplně.
- Obrázky: `out/check_body/mini_unfolded_detail_rear_car.png` (pohled řidiče auta 10 m za vlekem — světla ani SPZ
  nejsou), `…_detail_rear_tractor.png`, `…_detail_rear_corner_L.png`, `…_detail_sidemarker_L.png` (obryska skrz
  stěnu), `…_detail_side_section.png` (řez: světlo pod hranou plošiny), `mini_unfolded_side_reflectors_L.png`,
  `mini_unfolded_rear_low.png`, pro srovnání `mini_folded_rear_eye.png`.

Proč na tom záleží: `detachingMinLimit="0.98"` → rozložený vlek nejde odpojit, stojí tedy zapřažený a světla traktoru
se na něj přenáší.

### Návrhy oprav (Mini)

1. **Druhá sada zadních světel na konci rozložené plošiny** (vanilla postup u skládacích dílů — sdílená světla na
   pohyblivém uzlu): nová skupina `padRearLights` pod `padHingeEnd` (rozloženo z −4,44, y 0,72), v ní linkNody
   `padRearLight52_left/right` (x ±0,78, y ≈ −0,08 pod hranou panelu, osa Y dozadu jako u stávajících) + odrazky
   na čele panelu P. Ve složené bedně je panel P svislý a světla by mířila jinam → skrýt je přes `foldTrailer`:
   `<part node="padRearLights" startTime="7.5" endTime="7.6" startVisibility="true" endVisibility="false"/>`
   (panely jsou v rovině do D = 0,38, tj. čas ≤ 10,6 − 0,38·8 = 7,56 s). `sharedLight` má jen `staticLightCompound`,
   skrytím rodiče zhasne i svit. Volitelně druhá `licensePlate` (BACK) na stejném uzlu — FS25 umí víc tabulek.
2. **Zadní světla o 2 cm níž** (`rearLight52_left/right` y 0,62 → 0,60), ať se pouzdro nezařezává do panelu Z
   (vršek 0,668 < 0,676). Viditelnost to neřeší, jen průnik.
3. **Boční obrysky pryč z dosahu stěn**: posunout `sideMarker05_left/right` dopředu před stěnu, např. na zadní hranu
   blatníku (z ≈ 0,0, stěna končí u z −0,07, kolo začíná u z ≈ 0,10), nebo použít plochou obrysku; posun dolů je
   křehký (úhel stěny 100–165° podle terénu). Odrazky SideL/R2–3 buď přesunout na vnější (horní po sklopení) plochu
   stěn `Crate_Side*`, nebo je pod stěnou nechat a spolehnout se na SideL/R0–1 + obrysky.
4. Po úpravě pustit `blender -b --factory-startup --python out/check_body/scripts/analyze.py -- mini render`
   a `reflectors.py -- mini` (počítá přímo z exportovaného i3d).

### Middle/Max drobnosti

- Middle složený: roleta `tarpFrontRoll` (konec animace y 0,6025, z 2,5825) visí před předními odrazkami
  (y 0,63, z 2,547) → zvednout konec rolety nad 0,70 (jako u Max, kde je 0,9725 a odrazky čisté) nebo odrazky snížit.
- Max: `Underrun_Reflector0/1` (z −6,10) jsou 0,4 m zapuštěné za tažným zařízením a držákem SPZ — posunout na zadní
  hranu zábrany (z ≈ −6,45) nebo nechat (hlavní zadní odrazky `Reflector_RearL/R` jsou 100 %).

## 2. Vstupní a výstupní body

Mapování: všechny `i3dMapping` všech vozidel a objektů se rozřeší na existující uzel (0 chyb). Konvence spojek
(`findSinkAt`: lokální −X = ven) sedí u všech: pumpa, násypka, mlýnek, vodní ventily a vápenný vstup Middle/Max.

### Mini (`sprayDroneTrailerMini`)

| bod | výška | od obrysu | stav |
|---|---|---|---|
| `concentrateNeckNode` | 1,61 | 0,72 vpravo | OK, na víku `Tank_Induction_Lid`; ze země 1,90 m ≤ `HAND_POUR_PLAYER` 2,2 |
| `dieselNeckNode` | 1,41 | 0,53 vlevo | OK, na `Gen_0_Body`; 1,63 m |
| `exactFillRootNode` / diesel / koncentrát | 0,94 / 1,15 / 1,29 | — | OK, objemy uvnitř nádrží, kolizní (ne vizuální) |
| `fillTrigger` | střed 1,01 | — | OK, 2,46 × 2,02 × 4,6 m přes celý vlek |
| `fillHoseCoil/Start` | 0,91 / 0,76 | 0,58 vpravo | OK (start uvnitř bubnu navijáku záměrně) |
| `fillHoseNozzle` = `ParkPos` | 0,76 | — | OK, na objímce `HoseNozzle_Collar` |
| `Drone_S_FillPort` rozloženo | 1,42 | plošina z −2,88 | OK; dosah hadice hlídá `SprayDronePad.hoseReaches` (počítá se středem plošiny, port je 0,15 m vedle — kryje rezerva 10 %) |
| `batterySlotDeck1–4`, `batteryCharger` | 0,97 | 0,58–1,15 vlevo | OK, `ACTIVATE_DISTANCE` 2 m vodorovně |
| `chargerLid` | 1,15 | 0,80 vlevo | OK, v rozloženém stavu otevřené 100° |
| `toolboxActivateNode/2` | 1,33 | 0,60 | OK (referenční bod uprostřed bedny, 0,16 m od víka záměrně) |
| `plannerScreenNode` | 0,78 | 0,26 vzadu | OK: složeno je za boční stěnou bedny, ale `canUseScreen` chce rozložený vlek; rozloženo normála +Z míří ven doprava |
| `licensePlateBack` | 0,47 | — | rozloženo zakrytá, viz výš |
| `exitPoint` | 0 | 0,58 vně (rozloženo od stěny) | OK |

### Middle / Max

| bod | Middle | Max | stav |
|---|---|---|---|
| vodní ventily `waterHosePort*` | 0,92–1,18 m, 0,37–0,78 od pravého boku; ze země 1,14–1,54 m | 1,50–1,53 m, 0,60–0,66; **1,78 m** | OK (`PORT_DISTANCE` 1,9); u Max jen 12 cm rezerva |
| `limeInletNode` + `limeValveLever` | 1,36 m, 1,60 m | 1,70 m, **1,85 m** | OK, Max těsně (1,9) |
| `dieselNeckNode(2)` | 1,41 m → 1,70 | 1,69 m → 2,01 | OK (2,2) |
| `concentrateNeckNode` | 1,61 m → 1,98 | **2,32 m → 2,63 m** | **Max ze země MIMO** `HAND_POUR_PLAYER` 2,2; navíc 0,39 m nad hrdlem je `TopDeck_3`. Koncentrát u Max primárně plní skříň (vsátí), ruční nalévání jde jen z plošiny/žebříku — ověřit ve hře, případně zvětšit dosah pro tohle hrdlo nebo hrdlo vyvést do boku |
| `waterHoseEnd`, `limeHoseEnd` | skryté v i3d | skryté | OK, polohuje je `SprayDroneHoseLib.layoutChain` |
| `fillHose(B)Nozzle` = `ParkPos` | 2,54 m | 2,82 m | OK, na objímce |
| `ladderTrigger` | rozloženo 1,52 m, 0,14 od boku | 1,76 m, 0,19 | OK, potomek kloubu žebříku |
| `ladderGrab` Max | — | stojí na zemi (−2,02; 0; −1,75) i složené | OK, podle XML prázdný uzel bez funkce |
| `airIn/airOut/electric` | — | 0,82 m na oji | OK |
| baterie, relé, displej | OK | OK | `batterySlotDeck` ve 2,2–2,5 m, ale aktivace je vodorovná (2 m) |

### Mlýnek, pumpa, násypka, kufry

| bod | stav |
|---|---|
| `millOutletPort` | 0,70 m, 0,26 od pravého boku, −X ven; ze země 0,89 m | OK |
| big bag (`bagOutput nozzle -1.55 1.30 0`, `BAG_SPAWN_DROP` 1,95) | ústí (−2,55; 2,00; 0,15), kořen vaku 0,05 m nad zemí, 1,30 m vně obrysu; kvádr vaku 0,95 × 1,74 × 0,95 se s mlýnkem ani rourou neprotíná. `blowPipe` se zařezává jen do `Mill_PortCap` (v režimu big bag skrytý) a o pár mm do `Mill_Bin` u spojky | OK — `mill_bag_rear.png`, `mill_bag_side.png` |
| `millDieselNeck`, `millStartButton`, `millDustIn` | 1,26 / 1,21 / 1,20 m na povrchu | OK |
| `exactFillRootNode` mlýnku | střed 2,15 m, 1,72 × 1,10 × 1,56 v násypce | OK |
| `millPortCap` | uzel v počátku (skupina, mesh `Mill_PortCap` je u spojky) | OK |
| pumpa `pumpInletPort` (vlevo, 0,28 m) / `pumpOutletPort` (vpravo, 0,40 m) | na povrchu, −X ven | OK |
| pumpa `inHoseEnd/outHoseEnd/inStrainerEnd` | v i3d v počátku pod pumpou (sahají 6 cm pod zem), ale `showChain(h, false)` je při načtení skryje | OK |
| násypka `hopperFunnel` 1,04 m, `limeFillRootNode` otevřený shora, `hopperOutletPort` 0,40 m vpravo | OK |
| kufry `caseBatterySlot`, `casePad`, `caseLid`, `exactFillRootNode` | na povrchu / uvnitř dle účelu | OK |

## 3. Shrnutí podle závažnosti

1. **Mini rozložené: plošina zakrývá zadní světla a SPZ** zezadu z výšky oka ≥ 1 m (0 %), vlek přitom zůstává
   zapřažený → druhá sada světel na konci plošiny (bod 1 návrhů).
2. **Mini rozložené: boční stěny procházejí obryskami** a úplně kryjí boční odrazky 2–3 → přesunout obrysky před stěnu.
3. **Mini: pouzdra zadních světel o 12 mm v panelu Z** → světla o 2 cm níž.
4. **Max: hrdlo koncentrátu (2,32 m) je ze země mimo dosah ručního nalévání** (2,63 > 2,2 m) — ověřit z plošiny.
5. Drobnosti: Middle přední odrazky za spodní roletou (složeno), Max zapuštěné odrazky zábrany, Max ventily a vstup
   vápna jen 5–12 cm pod limitem `PORT_DISTANCE`.

## 4. Opraveno — Mini, body 1–3 (2026-10-29)

Změny v `blender/build_trailer_mini.py`, `blender/export_mini_mod.py`, šabloně `sprayDroneTrailerMini.xml.in`; Lua beze změny
(světla jsou pod `padHingeEnd`, takže je `applyPose` nese s plošinou včetně vyrovnání `padAnchor` podle terénu).

1. **Druhá sada na konci plošiny**: skupina `padRearLights` pod `padHingeEnd`, v ní `padRearLight52_left/right` (x ±0,58 — nožičky 5/6
   mají pouzdro od x 0,76; střed y 0,62, pouzdro 0,552–0,688 pod spodním lemem panelu P), `padPlateNumberLight03` a druhá SPZ
   `licensePlateBackPad` (`SQUARISH`, `placementArea 0.05 0.17 0.075 0.17`), vše na plechových konzolách na čele panelu P.
   `<sharedLight>` se stejnými soubory jako hlavní sada (`rearLight52_left/right.xml`, `plateNumberLight03.xml`) → stejné funkce
   (obrys, brzda, blinkry). Viditelnost: `<part node="padRearLights" startTime="7.5" endTime="7.6" startVisibility="true"
   endVisibility="false"/>` ve `foldTrailer` (čas 0 = rozloženo; D = (10,6 − t)/8, panely v rovině od D 0,38 = 7,56 s). V i3d
   viditelné jako `chargerCable` (čas 0 = model v i3d), složený vlek je skryje animace; v obrázku obchodu skryté (`_store_pose`).
2. **Obrysky a boční odrazky před stěnou**: `sideMarker05_left/right` z 1,28 na y(Blender) 0,02 (i3d z −0,02), mezi zadní hranou
   blatníku (−0,01) a začátkem boční stěny (0,07). Za kolem je místo dvou odrazek jedna (`SideL2/R2`, i3d z −0,03,
   `side_reflector_ys`); `SideL3/R3` zanikly (stěna by je zakryla v každé poloze).
3. **Hlavní zadní světla o 2 cm níž** (y 0,62 → 0,60): pouzdro už se do panelu Z nezařezává (clip prázdný).

Opakovaná kontrola (`analyze.py -- mini render`, `reflectors.py -- mini`, `mini_detail.py`):

| | složeno | rozloženo |
|---|---|---|
| `rearLight52_left/right` | 100 % | 46 % (zakryté plošinou jako dřív, nahrazuje je druhá sada) |
| `padRearLight52_left/right` | skryté | **100 %**, rovně zezadu ve všech výškách oka 100 % |
| SPZ `licensePlateBack` / `licensePlateBackPad` | 100 % / skrytá | 45 % / **100 %**, osvětlení SPZ 100 % |
| `sideMarker05_left/right` | 64 % (rovně 100 %) | 64 % (rovně 100 %), stěnou už neprochází; zbytek kryje blatník z úhlů zepředu |
| odrazky `SideL2/R2` (nové místo) | 60 % (rovně 100 %) | 27 % (rovně 100 %; zepředu blatník, zezadu sklopená stěna) |
| zadní odrazky `Reflector_RearL/R` | 100 % | 67 % (beze změny, kryje plošina) |

Obrázky: `out/check_body/mini_unfolded_detail_rear_car.png`, `…_pad_end_L.png`, `…_sidemarker_L.png`, `mini_unfolded_rear_eye.png`,
`mini_folded_rear_eye.png`; obchod `out/mod_build_mini/store_shot.png` (složený Mini, beze změny pózy).

Ve hře ověřit: druhá sada svítí a bliká jen na rozložené plošině a zhasne/zmizí při skládání (kolem 7,5 s), druhá SPZ má
čitelné číslo a nepřečnívá konzolu, na nerovném terénu konzoly (spodek 0,50 m pod horní plochou plošiny) nezajíždí do země.
