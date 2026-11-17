# Příkazy dev módu pro video v2 (N1 až N11)

Implementace: `tools/cinema/FS25_SprayDroneCinema/scripts/SprayDroneCinemaV2.lua` (nové), `SprayDroneCinemaScene.lua` (bagLift, canisterPour, spawnMod), `SprayDroneCinema.lua` (resolveNode `#`, `v2Frame`), `SprayDroneCinemaCamera.lua` (varování o chybějícím uzlu). Release mód beze změny, `SprayDroneDebug.ENABLED = false`.
Do běžící hry: `python tools/cinema/cinema_client.py reload` (poprvé po přidání souboru dvakrát, starý `reload` ještě nezná `SprayDroneCinemaV2`; `modDesc.xml` už soubor obsahuje, zip v Mods je ale zastaralý, přebalit `build.py` po vypnutí hry).
Testováno 2026-10-25 ve hře (slot 13, dvůr farmy, pole 3 a 4), kontrolní snímky `out/mod_build/v2_*.png`. Kroky scén jsou ve formátu `{"cmd": ..., parametry}`.

| příkaz | stav testu |
|---|---|
| N1 isolate | OK |
| N2 flightArea, worldLines | OK (worldLines jen zapíná příznak, čáry kreslí hra hráči u vleku, nezkoušeno vizuálně) |
| N3 coverLines | OK |
| N4 droneHover | OK (jeden i dva drony) |
| N5 toolboxSet, canisterPour from=box | OK na Middle; dráha kanystru je přímka a prochází rámem vleku |
| N6 bagLift target=mill | OK (vanilla big bag, mlýnek se naplnil) |
| N7 mark, seq | OK |
| N9 spawnCanister, spawnMod fill | OK |
| N10 screenWake | OK |
| N11 kamera `at="vlek#mapping"` | OK |

## N1 isolate

Parametry: `keep` (alias vleku, který zůstane; výchozí middle), `park` ("x,z" prvního místa na parkovišti, výchozí 260,-665), `spacing` (14 m, rozestup souprav v ose X), `yaw` (0), `props` (výchozí true: smaže `waterPump, waterTrailer550, limeHopper, sdtLimeMill, limeBigBag, bigBag_lime, relayPole` a všechny kanystry a pytle z modu), `vehicles=true` + `radius` (150) přesune i odpojená cizí vozidla kolem `keep` (bez zapřažení; `undo=true` je vrátí na původní místa). Ostatním soupravám SDT pošle `returnHome`, počká na zaparkování dronů, složí je a přenese přes `placeSet` (včetně tahače); hráč na konci jde zpět k `keep`. Ack přijde až po dokončení (dává se `timeout`, doba záleží na návratu dronů, 60 až 250 s).

```json
{"cmd": "isolate", "keep": "middle", "park": "250,-665", "spacing": 40, "timeout": 250}
{"cmd": "isolate", "undo": true}
```
Stav: OK. Zkoušeno i s drony ve vzduchu (dva drony Maxu v letu): přistály, souprava se složila a zaparkovala, rekvizity zmizely. Parkoviště je nutné mít vyzkoušené (kola OK, `groundCheck maxTilt 9`); testováno na 250,-665 se `spacing` 40. Vozidla přesunutá přes `vehicles=true` stojí na jedné řadě 25 m od řady souprav v ose Z bez kontroly terénu.

## N2 flightArea, worldLines

`flightArea`: `trailer`, `field` (výchozí vybrané pole; u `clear` jde i `all`), `mode` = `strip` | `points` | `clear`.
`strip`: pás šířky `width` (40) od bodu `back` (8) m za vlekem směrem ke středu pole, konec `inset` (15) m uvnitř pole. `points`: `pts="x,z;x,z;..."` (3 až `MAX_AREA_POINTS`). V odpovědi je kontrola `getCorridor` (jen pro právě vybrané pole). Plocha se ukládá do `vehicles.xml` při uložení hry, po natáčení `clear` (hra se při natáčení neukládá).
`worldLines`: `on` = true/false (příznak `SprayDroneStation.showWorldLines`).

```json
{"cmd": "selectField", "trailer": "max", "field": 2, "own": false}
{"cmd": "flightArea", "trailer": "max", "field": 2, "mode": "strip", "width": 40}
{"cmd": "flightArea", "trailer": "max", "mode": "points", "pts": "-700,160;-760,170;-780,205;-700,200;-690,175"}
{"cmd": "flightArea", "trailer": "max", "mode": "clear", "field": "all"}
```
Stav: OK. Plánovač po nastavení ukazuje fialovou plochu a text „Letová plocha: N bodů“ (`v2_area_strip.png`, `v2_area_points.png`). `selectField own=false` pole nekupuje (pole 3 a 4 jsou už vlastní).

## N3 coverLines

Parametry: `trailer`, `field` (výchozí vybrané), `keep` = "k0,k1" (čísla řádků od 0 od okraje pole, i rozsah "3-4") nebo `auto2` (dva sousední řádky uprostřed). Všechno ostatní včetně úvratí a ostrovů se označí za postříkané (jako `dbgCmd coverField`), `markRouteDirty` + `raiseCoverage`. Předtím `resetField` není nutný (záznam se přepíše), pole musí potřebovat postřik (`setField crop=MAIZE growth=3`, jinak plánovač hlásí „pole je hotové“) a musí být vybrané.

```json
{"cmd": "setField", "field": 4, "crop": "MAIZE", "growth": 3}
{"cmd": "selectField", "trailer": "max", "field": 4, "own": false}
{"cmd": "coverLines", "trailer": "max", "field": 4, "keep": "auto2"}
{"cmd": "startFlight", "trailer": "max", "drone": 0, "fill": true}
```
Stav: OK. Pole 4 (6 řádků po 9 m): plánovač ukáže dva žluté řádky, za letu stříká dron 1 řádek x=-693,5 a dron 2 sousední x=-702,5 (rozteč 9 m = záběr), start dronu 2 se opožďuje o ~10 s (čekání na plošinu).

## N4 droneHover

Parametry: `trailer`, `drone` (1; 0 = všechny), `seconds` (5), `delay` (s po vzletu, než se dron zastaví; 0), `wait=true` čeká na konec visení. Čas začíná, až když je dron ve vzduchu. Obálka na `SprayDroneStation.updateFlight`: dron drží pozici, rotory běží, baterie se nevybíjí, vítr, signál a pohyb vleku se nekontrolují. Po vypršení let pokračuje po stejné trase. Příkaz se zadává před `startFlight`.

```json
{"cmd": "droneHover", "trailer": "max", "drone": 0, "seconds": 6, "delay": 2}
{"cmd": "startFlight", "trailer": "max", "drone": 0, "fill": true}
```
Stav: OK. Jeden dron: 6 s beze změny polohy a baterie, potom pokračuje. Dva drony: každý visí od svého vzletu. `delay` ≥ 3 s doporučeno u Maxu, jinak se dron zastaví ještě ve stoupání (u dronu 2 se výška při visení dál mírně mění o 1 až 2 m).

## N5 toolboxSet, canisterPour from=box

`toolboxSet`: `trailer`, `open` (true/false, idempotentní, mění jen když se stav liší), `part` (all | číslo bedny; Mini má dvě), `fill=true` (naplní police jako `dbgCmd toolboxFill`), `wait=true` (čeká na doběh víka).
`canisterPour` nové: `from=box`, `slot=n` (bez `slot` první obsazený; bez `fill` druh i litry podle slotu). Kanystr vznikne na poloze uzlu `toolboxCanister<n>`, slot je během pohybu skrytý a po konci se vrátí (kanystr se po vylití smaže, slot zůstane obsazený).

```json
{"cmd": "toolboxSet", "trailer": "middle", "open": true, "fill": true, "wait": true}
{"cmd": "playerTo", "x": -690, "z": 160, "force": true}
{"cmd": "canisterPour", "trailer": "middle", "from": "box", "slot": 8, "tLift": 2, "tTilt": 2, "tPour": 6}
```
Stav: OK na Middle (nalito 20 l, sloty 8 a 9, slot se po akci znovu zobrazí). Omezení: hráč musí být do 15 m od bedny (`playerTo force=true`), dráha z police k hrdlu je přímka a kanystr při ní prochází rámem vleku (u záběru zblízka zkusit jiný `tLift` nebo záběr z boku). Mini (dvě bedny) nezkoušeno.

## N6 bagLift target=mill

Parametry jako dosud (`side`, `dx`, `dz`, `up`, `tLift`, `tMove`, `tLower`, `tHold`, `keep`, `fill`, `yaw`) plus `target=mill` a `mouth` (0,8 m: výška big bagu nad středem obálky ústí). Big bag je vanilla `data/objects/bigBag/lime/bigBag_lime.xml` (druh LIME, `fill` l, výchozí 300). Ústí mlýnku je střed obálky kolizního kvádru `exactFillRootNode` (počátek uzlu leží u země, proto ne `getWorldTranslation`). Zbytek jako u násypky (kinematické vedení, vyklopí se sám, po vyprázdnění ho za 1,5 s smaže).

```json
{"cmd": "spawnMod", "rel": "vehicles/sdtLimeMill/sdtLimeMill.xml", "x": -664, "z": 132, "yaw": 0}
{"cmd": "bagLift", "target": "mill", "fill": 300, "tHold": 25}
{"cmd": "bagStatus"}
```
Stav: OK. Mlýnek měl 0 l, po 8 s 300 l hrubého vápna (`bagStatus`: „mlýnek hrubé 300 l“); `millDbg millFill` + `millOn` pak mele (jemné vápno roste, log `SDT MILL`). Starý `bagStatus` navíc hlásí hladiny mlýnku.

## N7 mark, seq

`mark`: `name`; log `CINEMA t=<g_time> ... MARK <name>`.
`seq`: `steps="t akce k=v k=v; t akce ..."` (t v sekundách od přijetí příkazu, měřeno uvnitř hry; hodnoty bez mezer a středníků, nejde `keys=` pro kamery), ack po provedení všech kroků včetně čekání (`wait*`), `timeout` pro celou sekvenci. Selhání kroku se zapíše a sekvence pokračuje.

```json
{"cmd": "seq", "timeout": 60, "steps": "0 mark name=start;0.4 startFlight trailer=middle fill=true;4 droneStatus trailer=middle;8 droneStatus trailer=middle"}
```
Stav: OK. Rozestupy kroků 0,09 až 0,15 s (po 0,1 s zadaných), bez jitteru souborového dotazu. Příkazy s `keys` (camPath) se sekvencí nespouštějí.

## N9 spawnCanister, spawnMod fill

`spawnCanister`: `kind` = fertilizer | herbicide | diesel | limebag, `x`, `z`, `yaw` (stupně), `liters` (20; pytel 50), `lift` (0,15 m nad terénem), `still=true` (kinematické), `trailer` (kterýkoli vlek SDT s bednou, výchozí první; vlek tam stát nemusí). Hráč se přenese do 30 m od místa.
`spawnMod`: nově `fill=<FILLTYPE>`, `liters` (výchozí plná kapacita), `still=true`; `mod=base` bere `rel` jako cestu v datech hry. Hladina se nastavuje rozdílem, ne vyprázdněním (vanilla big bag a palety se po vyprázdnění sami smažou, `C.setFillLevel`).

```json
{"cmd": "spawnCanister", "kind": "limebag", "x": -666, "z": 140, "yaw": 90}
{"cmd": "spawnMod", "rel": "objects/limeBigBag/limeBigBag.xml", "x": -668, "z": 142, "fill": "SDT_FINE_LIME", "liters": 500}
{"cmd": "spawnMod", "mod": "base", "rel": "data/objects/bigBag/lime/bigBag_lime.xml", "x": -664, "z": 142, "fill": "LIME", "liters": 300}
```
Stav: OK (čtyři druhy kanystrů a pytel, big bag s 500 l jemného i 300 l hrubého vápna, snímek `v2_canisters.png`). Drony S/M/L a baterie (klonování) se nedělaly.

## N10 screenWake

`screenWake`: `trailer`, `off=true` displej uspí (zkouška). Nastaví `screenWakeTime` kořene vleku. Stav: OK: po `off=true` je uzel `plannerScreenOn` neviditelný, po `screenWake` viditelný.

## N11 kamera `at="vlek#i3dMapping"`

`resolveNode` bere za `#` jméno i3dMapping (začíná písmenem), číslo za `#` je dál pořadí nálezu vozidla (`middle#2`). Platí pro `at`/`tat` v `camPath`, `camSet` a pro `target` v `camOrbit`/`camFollow`. Offsety `x,y,z` jsou jako dosud v souřadnicích uzlu jen s natočením kolem svislé osy (`full=1` pro celé natočení). Neznámé jméno: varování v logu „uzel ... nenalezen“ a souřadnice se berou světově.

```json
{"cmd": "camSet", "at": "middle#concentrateNeckNode", "x": -1.5, "y": 0.9, "z": -1.5, "tat": "middle#concentrateNeckNode", "tx": 0, "ty": 0, "tz": 0, "fov": 40}
```
Stav: OK (snímek `v2_cam_mapping.png`).

## Nedělané

N8 (hideHotspots), N12 (droneDock), klonování dronů a baterií.

## Stav světa po zkouškách

Slot 13: vleky Mini a Max zaparkované na 250,-671 a 290,-671 (původně 244 a 284 na z=-665), Middle s pickupem na původním místě (-696,167), Max složený. Pole 4 má `setField MAIZE growth 3` (jako dříve), trailery Middle a Max mají dál vybrané pole 4 (příkaz `selectField field=0` výběr nezruší). Letové plochy a pokrytí vymazány, rekvizity smazány, čas odemčen (`setTime hour=12 lock=false`, před zkouškami byla noc), bedna Middle zavřená a plná kanystrů, koncentrát prázdný.
