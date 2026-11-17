# Natáčecí plán: video SprayDrone v2

Role kameraman (`prompts/03_navrh_scen.md`). Vstup: `scenar.md` (verze 2), `review_technik.md`, `lokace.md`, průzkumné snímky `out/trailer/survey/`. **Akce, kamery i tento plán jsou generované** skripty `tmp/v2/gen_*.py` (konstanty míst a časů: `tmp/v2/gen_common.py`; po opravě souřadnic stačí `python tmp/v2/gen_main.py`, přepíše `scenes/*` i tento soubor). Souřadnice, které nejsou ověřené ve hře, jsou označeny **„ověřit průzkumem“**.

## 1. Souhrn

| | |
|---|---|
| akcí | **33** |
| kamer (takes) | **106** (mini 34, middle 33, max 33, spol 2, prod 4) |
| záběrů scénáře | 92, každý ≥ 2 kamery (CHYBA: [('max-3.1', 0)]) |
| odhad natáčení (čistý) | **4 h 50 min** (17386 s po sekvencích; take = příprava + čekání + záznam + 45 s režie) |
| odhad s opravnými pokusy (+30 %) | **6 h 17 min** |

`mk_take.py --dry` projde všechny kombinace akce × kamera (viz kap. 8).

## 2. Konvence

- **Souřadnice:** FS25, osa +x východ, +z směrem „strana vody u POLO“ (z roste k jihu podle `b02`/`b03`; hlavní agent v hlášení označuje stranu +z jako sever – rozhoduje znaménko z). Yaw: 0 = k +z, 90 = k +x, 180 = k −z, 270 = k −x. Lokální osy vozidla: +z dopředu, **+x vlevo, −x vpravo**; ventily, žebřík, hrdlo koncentrátu a vápnová spojka jsou na **pravém boku (−x)** (podle i3d), proto stojí soupravy pravým bokem k vodě / ke kameře (dvůr a POLO yaw 90 → pravý bok k +z; POTOK yaw 180 → pravý bok k východu).
- **Kamera:** `at="<vozidlo>"` = lokální souřadnice vozidla (jen yaw se bere z vozidla), `tat` totéž pro cíl; světové polohy jsou `rel: terrain` (y nad terénem). `at="max:drone1"` je uzel dronu. Statický záběr = `camPath` se dvěma stejnými klíči (krok `camSet` s aliasem vozidla nejde, `at` je v `mk_take` čas). `camPath` v kam-souborech nikdy nemá `wait`.
- **Čas v klipu:** `at` je čas od značky `{"kamera": true}`; klip začíná o `lead` 0,5 s dřív (+ latence OBS ≈ 0,2 s). Akce vždy začíná po 2,0 s rezervy a končí 2 s rezervy před `record stop`. Kamery spojené s událostí s nedeterministickým časem (let, přistání) jdou přes `after` značku v akci; v oknech ± 0,5 s nic diskrétního nestřihnout (kap. 6 `review_technik.md`).
- **Reset každé akce (hlava):** `setWeather SUN`, `setTime lock=true` (podle scénáře 10:00–14:00), `setFog reset`, `setField`, `returnHome`+`waitDrone parked`, `isolate` (ostatní soupravy pryč, rekvizity a cizí vozidla pryč), `play windOff` (lety), `placeSet` (složený) → `fold unfold wait` → `selectField`/`resetField`/`setTank`/`fillSet`/`generator`/`dbg whDrop`/`toolboxSet open=false`, pauza 6 s, `groundCheck`; potom jediný krok `{"kamera": true}`, `record start lead 0.5`, akce, `record stop`. U Middle `nodeVis` zobrazí anténu a GPS před rozložením. Jízdní akce startují s rozjezdem před záznamem (`driveTo` + pevná pauza).
- **Nové příkazy dev módu** (`SprayDroneCinemaV2.lua`): `isolate`, `toolboxSet`, `canisterPour from=box slot=`, `bagLift target=mill`, `droneHover`, `coverLines`, `flightArea`, `screenWake`, `spawnCanister`, `mark`. U nekritických je `optional`.
- **Plánovač (UI):** akce otevře `ui plannerOpen`, kamera jsou jen pohyby mapy (`plannerView`, `plannerField pan zoom`) a pohled na displej na vleku. Po UI akci `ui close` + `camStop` (F6).

## 3. Místa a konstanty (ověřit průzkumem)

| kód | souřadnice | stav |
|---|---|---|
| SIL | osa z = −662,5, jízda na západ, x 90 → −95; kamery na straně z > −662,5 | ověřeno `b02_road`/`b02_front` jen pro x +76 … −80 a z = −636 (kamera); **ověřit** úsek do x ≈ ±95, krajnici z −649…−657, azimut slunce |
| CESTA | z = 172,5, x −655 → −830 | ověřeno `b03_gravel` |
| DVŮR | souprava tahač (−690, 140) yaw 90; příjezd od x = −735; odjezd na východ (−560, 140) | poloha ověřena (`b04`, `c33`), **příjezd a odjezd ověřit** |
| POLO | tahač (-625, 455) yaw 90, vlek ≈ (−631, 455), voda a rákos od z ≈ 470, jízda po z = 455 od x -735 | **ověřeno hlavním agentem** (louka rovná); cesta (3.1, 8.2): **ověřit**; nízké kamery na straně −z kolem (−605, 440) nepoužívat (terénní vlna, stromy); dobré: od vody (−630, 490, y 3–15) a ze západu (−665, 455) |
| POTOK | kořen Maxu (674, -37.0), tahač 674.0, -43.2, yaw **180 (doladit)**; potok diagonálně SV–JZ, voda ≈ 4 m za pumpou | hlavní agent ověřil rig tahač (674, −30) yaw 0 a pumpu `(680, −36)` s `whPond/whOut` OK; **natočení rovnoběžně s potokem doladit**, pravý bok (−x) má jít k vodě |
| silnice u POTOKU | E–W silnice z ≈ -84 s mostem přes potok kolem x ≈ 708; jízda x 830 → 610; odbočka (686, -84) → pás | odhad z leteckého snímku – **ověřit** (poloha, přímost, nájezd na pás, rychlost) |
| pole | Mini: 4 (−697, 235); Middle: 91 (−710, 701, 264 m od vleku); Max: blízké 59 (635, 25), vzdálené 60 (535, 33; strniště `setField growth=cut`) | ID z `fields_dash.json`, **ověřit** vlastnictví, dosah, plodinu |
| PARK | isolate: `260,-665` (výchozí), u SIL `-690,150` | **ověřit**: volné, mimo dohled a mimo okno plánovače |
| BET | náhrada: dvůr (-712, 152), řada podél x, tahače na z = 118 | **určí průzkum** (rovný beton) |

### Co je potřeba ověřit průzkumem (souhrn pro hlavního agenta)

- **Slunce:** azimut a výška v 10:00–14:00 a že kamery označené „slunce vzadu“ ho opravdu mají vzadu (vše se odvíjí od strany +z).
- **Detaily vleků (beat 4):** souřadnice cílů D1–D5 počítané z i3d (`tmp/v2/i3d_nodes.py`, rotace nadřazených uzlů zanedbána) – kontrolní snímek před natáčením; nebo `at="vlek#uzel"`.
- **Délky animací:** `fold unfold` Mini 12 s / Middle ≈ 10 s / Max ≈ 9 s; víko bedny ≈ 2 s; `canisterPour` 2 + 2 + 6 + 3 s.
- **Dráhy dronů:** směr řádků polí 4, 91, 60 (statické záběry TOP a 7.4 po kalibračním běhu `trace on`), volný sloupec nad plošinami.
- **fillType:** `HERBICIDE` v hlavní nádrži Mini (jinak špatná barva mlhy), `LIQUIDFERTILIZER`, `SDT_FINE_LIME`.
- SIL: souvislá přímá silnice od x ≈ 95 do −95 (ověřeno jen +76…−80)
- kamery na jižní krajnici (z −649,5…−657,5): volné, bez keřů do 1 m od objektivu
- azimut slunce v 10:00 a že A, D nemají slunce v objektivu
- azimut slunce v 11:00 a že A, D nemají slunce v objektivu
- azimut slunce v 12:00 a že A, D nemají slunce v objektivu
- pozice C (−745, 168) a B (sever, 26 m od cesty): volné, mimo plot/keře
- start (−735, 140) a trasa po z = 140 jsou průjezdné (c61/c62 používaly mlýnek na (−740…−748, 150…158))
- doba animace 12 s
- po `fold unfold` stojí dron na heliportu a vrtule nejsou roztočené
- souřadnice cílů D1–D5 podle uzlů (kap. 5 scénáře) – kontrolní snímek před natáčením
- D3: je truhla po rozložení otevřená?
- slot 1 leží v pravé bedně nejblíž hrdlu (toolboxCanister1 = (−0,70; 0,76; 1,23))
- police obsahují jen herbicid (jinak štítky jiných látek v záběru)
- plannerPage 2 = karta plánu (a 3 = Let?)
- screenWake probudí displej viditelně
- cizí ikony v okně mapy při zoom 1,8
- jméno fillType herbicidu (HERBICIDE) a že dron stříká bílomodrou mlhu
- pole 4: vlastnictví (own) a dosah
- směr řádků pole 4 pro statický záběr 7.4 (kalibrační běh `trace on`)
- `waitDrone near` 28 m dává dost času pro 7.5
- poloha šachty baterií vůči dronu v kamerách B, D
- trasa odjezdu z dvora (z = 140 → x = −560)
- přímý průjezdný úsek z = 455 od x = -735 do -675 (stromy, rákos)
- umístění kamer C, B (voda jižně)
- POLO: místo (-625, 455) je rovné a volné, voda a rákos jižně od z ≈ 465
- kamery A–D stojí na souši
- doba rozložení ≈ 10 s (foldLadder 5 s + dron)
- stožár se při rozložení vysune viditelně (O10)
- souřadnice cílů D1–D5 (kap. 5 scénáře) – kontrolní snímek
- D2: plachta na pravém boku (TarpTrack_R) je rozvinutá
- trajektorie kanystru z police 1 (zadní skříň) k hrdlu na pravém boku (průchod karoserií?)
- police obsahují jen hnojivo
- ID pole jižně od poloostrova = 91 (střed (−710, 701), 4,23 ha), vlastnictví a dosah
- plannerPage 2 = karta plánu
- volný svislý sloupec nad plošinou a osa stoupání ≥ 25 m (O5)
- jméno LIQUIDFERTILIZER a pole 91 vlastnitelné (own)
- palubní kamera: osa uzlu dronu
- směr příletu dronu od pole (jih) vůči kamerám A, D
- odjezdová trasa na východ z POLO
- POTOK: místo, vzdálenost tahač–kořen Maxu (odhad 12,6 m), rovina 30 × 25 m
- orientace: potok na východě x ≈ 686 (z průzkumných snímků)
- doba rozložení ≈ 9 s
- oba drony se rozloží najednou
- souřadnice cílů D1–D5 podle uzlů – kontrolní snímek
- D3: víka kapes navíječů otevřená po rozložení
- whPond najde vodu ≥ 0,15 m do 8 m od vstupní spojky pumpy (pumpa ≈ (677.2, -30.0), potok x ≈ 686)
- pumpa stojí na straně ventilu (pravý bok = −x v souřadnicích Maxu, ne levý jako píše scénář)
- po removeVehicle ventil volný a žádná hadice nevisí
- číslo vápnové spojky pro `dbg whConnect<N>` (5 z c63c) – `dbg whStatus`
- bagLift target=mill vyklopí big bag do mlýnku (N6)
- poloha mlýnku (677.8, -26.0) stojí na souši, ≤ 8 m od spojky
- prstenec `millStartRing` svítí při millOn
- ID polí u POTOKU: blízké 59 (brambory, střed (635, 25)), vzdálené 60 (535, 33); pole 60 jako strniště (`setField growth=cut`)
- body plochy (HOME ≈ (674, -29)) – plocha po každém bodu hned vidět
- plannerPage 2 = karta s pruhem výšky přeletu
- planner nekreslí přelety ani překážky (jen fialová plocha)
- coverLines: sousední dráhy dvou dronů (čísla řádků od okraje pole, auto2)
- dron 2 startuje s odstupem ≈ 3 s
- pole 60 jako strniště a v dosahu dronů (153 m)
- dron 2 přistává po drony 1 (přední plocha první) a nezačne servis dřív než dron 1
- trasa z pásu k silnici na sever (přejezd příkopu)
- `droneHover` drží drony nad vleky po vzletu (výška, doba)
- výkon hry se 4 drony (≥ 55 fps)
- zachování mezer mezi vleky
- BET: rovný beton (průzkum určí; náhrada = dvůr)
- yaw předmětů: štítky směrem k +z
- spawnCanister kind=limebag, spawnMod big bag s fill SDT_FINE_LIME
- relé tyč rozložená a zelený LED po `relaySpawn`
- `padDrone` M pro Middle a L pro Max
- tahače na z = 118 mají volné místo (pole 1 na severu)
- baterie viditelné v truhle Mini

## 4. Pořadí natáčení (podle místa a nastavení světa)

Hra: slot 13, před sezením `nvidia-smi`, `ollama ps`, OBS, `cinema_client ping`; mezi bloky se mění jen poloha souprav (`isolate` + `placeSet`, ≈ 1 min). Vlek jedné akce se vždy natáčí všemi kamerami za sebou (A, B, C, D), svět se mezi nimi resetuje hlavou akce.

| blok | místo a svět | akce (pořadí) | takes | odhad |
|---|---|---|---|---|
| 1 | Silnice SIL (beaty 1–2 Mini a Middle), jedno nastavení světa, jen přestavba soupravy | mini-silnice, middle-silnice | 8 | 17 min |
| 2 | Dvůr farmy a štěrková cesta: film mini | mini-cesta, mini-dvur-prijezd, mini-rozlozeni, mini-detaily, mini-kanystr, mini-planovac, mini-let, mini-navrat-servis, mini-slozeni-odjezd | 30 | 1 h 18 min |
| 3 | Poloostrov u velké vody (POLO): film middle | middle-cesta, middle-polo-prijezd, middle-rozlozeni, middle-detaily, middle-kanystr, middle-planovac, middle-let, middle-navrat-servis, middle-slozeni-odjezd | 29 | 1 h 19 min |
| 4 | Potok u pole (POTOK): film max | max-silnice, max-zaparkovani, max-rozlozeni, max-detaily, max-pumpa, max-mlynek, max-planovac, max-let, max-navrat-servis, max-slozeni-odjezd | 33 | 1 h 35 min |
| 5 | Dvůr farmy: epilog a produktová scéna | spol, prod-rada, prod-vleky | 6 | 21 min |

## 5. Tabulka akcí

| akce | film · beat | místo · čas | záběry | kamery | záznam (s) | take (s) | takes · odhad |
|---|---|---|---|---|---|---|---|
| `mini-silnice` | mini · 1-2 | SIL (asfaltka z = −662,5, jízda na západ) · 10:00 | mini-1.1, mini-2.1 | ABCD | 18 | 128 | 4 · 8 min |
| `middle-silnice` | middle · 1-2 | SIL (asfaltka z = −662,5, jízda na západ) · 11:00 | middle-1.1, middle-2.1 | ABCD | 18 | 128 | 4 · 8 min |
| `mini-cesta` | mini · 3 | CESTA (štěrková cesta z = 172,5 ke stodole, ověřeno b03) · 10:10 | mini-3.1 | ABCD | 12 | 117 | 4 · 8 min |
| `mini-dvur-prijezd` | mini · 3 | DVŮR (−690, 140) · 10:10 | mini-3.2 | ABCD | 16 | 121 | 4 · 8 min |
| `mini-rozlozeni` | mini · 4 | DVŮR (−690, 140), yaw 90, pravý bok k jihu · 10:20 | mini-4.1 | ABCD | 18 | 138 | 4 · 9 min |
| `mini-detaily` | mini · 4 | DVŮR (−690, 140), rozložený Mini · 10:22 | mini-4.2, mini-4.3, mini-4.4, mini-4.5, mini-4.6 | AB | 30 | 150 | 2 · 5 min |
| `mini-kanystr` | mini · 5 | DVŮR (−690, 140), rozložený Mini · 10:30 | mini-5.1, mini-5.2 | ABCD | 22 | 147 | 4 · 10 min |
| `mini-planovac` | mini · 6 | DVŮR (−690, 140), plánovač (celoobrazovkový) · 10:40 | mini-6.1, mini-6.2, mini-6.3 | AB | 24 | 144 | 2 · 5 min |
| `mini-let` | mini · 7 | DVŮR → pole 4 (−697, 235) · 10:45 | mini-7.1, mini-7.2, mini-7.3, mini-7.4 | ABC | 60 | 225 | 3 · 11 min |
| `mini-navrat-servis` | mini · 7 | DVŮR (−690, 140) · 11:00 | mini-7.5, mini-7.6, mini-7.7 | ABCD | 24 | 219 | 4 · 15 min |
| `mini-slozeni-odjezd` | mini · 8 | DVŮR → odjezd na východ (z = 140) · 11:30 | mini-8.1, mini-8.2 | ABC | 27 | 147 | 3 · 7 min |
| `middle-cesta` | middle · 3 | cesta k POLO (z = 455, x od -735) · 11:10 | middle-3.1 | ABCD | 12 | 116 | 4 · 8 min |
| `middle-polo-prijezd` | middle · 3 | POLO (-625, 455), voda jižně · 11:15 | middle-3.2 | ABCD | 17 | 122 | 4 · 8 min |
| `middle-rozlozeni` | middle · 4 | POLO, yaw 90 · 11:20 | middle-4.1 | ABCD | 16 | 136 | 4 · 9 min |
| `middle-detaily` | middle · 4 | POLO, rozložený Middle · 11:22 | middle-4.2, middle-4.3, middle-4.4, middle-4.5, middle-4.6 | AB | 30 | 150 | 2 · 5 min |
| `middle-kanystr` | middle · 5 | POLO, rozložený Middle · 11:30 | middle-5.1, middle-5.2 | ABC | 22 | 147 | 3 · 7 min |
| `middle-planovac` | middle · 6 | POLO, plánovač · 11:40 | middle-6.1, middle-6.2, middle-6.3 | AB | 24 | 144 | 2 · 5 min |
| `middle-let` | middle · 7 | POLO → pole 91 (−710, 701) · 11:45 | middle-7.0, middle-7.1, middle-7.2, middle-7.3, middle-7.4 | ABC | 75 | 255 | 3 · 13 min |
| `middle-navrat-servis` | middle · 7 | POLO · 12:05 | middle-7.5, middle-7.6, middle-7.7 | ABCD | 24 | 254 | 4 · 17 min |
| `middle-slozeni-odjezd` | middle · 8 | POLO → odjezd na východ · 12:30 | middle-8.1, middle-8.2 | ABC | 26 | 146 | 3 · 7 min |
| `max-silnice` | max · 1-2 | SIL (asfaltka z = −662,5, jízda na západ) · 12:00 | max-1.1, max-2.1 | ABCD | 18 | 128 | 4 · 8 min |
| `max-zaparkovani` | max · 3 | POTOK (674, -37), yaw 180 · 12:10 | max-3.2 | ABCD | 16 | 121 | 4 · 8 min |
| `max-rozlozeni` | max · 4 | POTOK, yaw 180 (pravý bok k potoku) · 12:20 | max-4.1 | ABCD | 16 | 136 | 4 · 9 min |
| `max-detaily` | max · 4 | POTOK, rozložený Max · 12:22 | max-4.2, max-4.3, max-4.4, max-4.5, max-4.6 | AB | 30 | 150 | 2 · 5 min |
| `max-pumpa` | max · 5m | POTOK, pumpa mezi vlekem a potokem · 12:35 | max-5m.1, max-5m.2, max-5m.3, max-5m.4 | ABCD | 18 | 153 | 4 · 10 min |
| `max-mlynek` | max · 5m | POTOK, mlýnek za pravým bokem Maxu · 12:42 | max-5m.5, max-5m.6, max-5m.7, max-5m.8 | ABC | 32 | 167 | 3 · 8 min |
| `max-planovac` | max · 6 | POTOK, plánovač · 13:05 | max-6.1, max-6.2, max-6.3, max-6.4 | AB | 30 | 156 | 2 · 5 min |
| `max-let` | max · 7 | POTOK → pole 60 (535, 33) – strniště · 13:15 | max-7.0, max-7.1, max-7.2, max-7.3, max-7.4 | ABC | 90 | 295 | 3 · 15 min |
| `max-navrat-servis` | max · 7 | POTOK · 13:30 | max-7.5, max-7.6, max-7.7 | ABCD | 26 | 271 | 4 · 18 min |
| `max-slozeni-odjezd` | max · 8 | POTOK → odjezd k severu · 13:45 | max-8.1, max-8.2 | ABC | 26 | 152 | 3 · 8 min |
| `spol` | spol · epilog | DVŮR (−694, 138), tři vleky (c02_three_wide) · 13:00 | spol-1, spol-2, spol-3 | AB | 36 | 211 | 2 · 7 min |
| `prod-rada` | prod · prod | BET (náhrada: dvůr, -712, 152) · 13:00 | prod-2, prod-3, prod-4, prod-5, prod-8 | AB | 50 | 205 | 2 · 7 min |
| `prod-vleky` | prod · prod | BET (náhrada: dvůr), vleky v pozadí · 13:00 | prod-1, prod-6, prod-7 | AB | 28 | 213 | 2 · 7 min |

## 6. Akce podrobně

### Blok 1: Silnice SIL (beaty 1–2 Mini a Middle), jedno nastavení světa, jen přestavba soupravy

#### `mini-silnice`

- **Pokrývá:** mini-1.1, mini-2.1. **Místo a čas:** SIL (asfaltka z = −662,5, jízda na západ), 10:00.
- **Akce:** Souprava stojí na x = 90, yaw 270; tahač jede na západ do x = -95 rychlostí 36 km/h (mode line), záznam začíná 4,5 s po rozjezdu (souprava kolem x ≈ 60). 
- **Izolace:** isolate keep=mini park=-690,150 props vehicles=true; ostatní soupravy parkují u farmy, mimo silnici.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** slunce: jih, kamery jen z jižní strany nebo zpoza kamery; sklon silnice 6,4° (groundCheck maxTilt 9); jízda nedeterministická (průjezd ±0,7 s, bočně ±0,3 m).
- **Ověřit průzkumem:** SIL: souvislá přímá silnice od x ≈ 95 do −95 (ověřeno jen +76…−80); kamery na jižní krajnici (z −649,5…−657,5): volné, bez keřů do 1 m od objektivu; azimut slunce v 10:00 a že A, D nemají slunce v objektivu.
- **Soubory:** `scenes/mini-silnice.akce.json`, `mini-silnice.kamA.json`, `mini-silnice.kamB.json`, `mini-silnice.kamC.json`, `mini-silnice.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | tele ze západního konce silnice proti jízdě, souprava roste z dálky | C | STAT (pomalé oddálení) · – | 14 → 22 | 1,2 m nad krajnicí, z = −656 | mini-1.1 0–8 |
| B | těsný průjezd z jižní strany, švenk po směru jízdy, konec ve 3/4 zezadu | PC→C | PAN-L (po směru jízdy) · R→L | 30 → 36 → 32 | 1,4 m, z = -649,5 (13 m od osy) | mini-2.1 0,5–8,5 |
| C | ověřený záběr b02_road: pevná kamera 26 m od osy, švenk za tahačem | PC | PAN-L · R→L | 32 → 38 → 32 | 1,6 m, z = −636 (ověřeno) | mini-2.1 0–7,5 |
| D | nízký tele pohled od konce silnice (druhá varianta 1.1), souprava projede těsně u kamery | C | STAT, tele, nízko · – | 12 | 0,8 m, z = −657,5, x = −80 | mini-1.1 0–9 |

Rizika kamer: **A**: slunce vpravo (jih), jízdní stopa přímá; kamera ve stínu nesmí být; souprava se rozjíždí 4,5 s před záznamem (start x = 90). **B**: průjezd v čase ≈ 4 s (x kamery 20 = poloha soupravy 60 − 10 m/s · 4 s); odchylka ±0,7 s; keře na jižní straně ověřit. **C**: geometrie převzata z b02_road (ověřená), čas 10:00 místo 18:00 – slunce teď vzadu vpravo. **D**: kamera 5 m od osy: souprava proletí kolem v čase ≈ 14 s (mimo použitou část); Z4 – tráva v popředí do 1 m.

#### `middle-silnice`

- **Pokrývá:** middle-1.1, middle-2.1. **Místo a čas:** SIL (asfaltka z = −662,5, jízda na západ), 11:00.
- **Akce:** Souprava stojí na x = 90, yaw 270; tahač jede na západ do x = -95 rychlostí 36 km/h (mode line), záznam začíná 4,5 s po rozjezdu (souprava kolem x ≈ 60). Pickup s vlekem Middle (dron na střeše, plachty svinuté, žebřík složen).
- **Izolace:** isolate keep=middle park=-690,150 props vehicles=true; ostatní soupravy parkují u farmy, mimo silnici.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** slunce: jih, kamery jen z jižní strany nebo zpoza kamery; sklon silnice 6,4° (groundCheck maxTilt 9); jízda nedeterministická (průjezd ±0,7 s, bočně ±0,3 m).
- **Ověřit průzkumem:** SIL: souvislá přímá silnice od x ≈ 95 do −95 (ověřeno jen +76…−80); kamery na jižní krajnici (z −649,5…−657,5): volné, bez keřů do 1 m od objektivu; azimut slunce v 11:00 a že A, D nemají slunce v objektivu.
- **Soubory:** `scenes/middle-silnice.akce.json`, `middle-silnice.kamA.json`, `middle-silnice.kamB.json`, `middle-silnice.kamC.json`, `middle-silnice.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | tele ze západního konce silnice proti jízdě, souprava roste z dálky | C | STAT (pomalé oddálení) · – | 14 → 22 | 1,2 m nad krajnicí, z = −656 | middle-1.1 0–8 |
| B | těsný průjezd z jižní strany, švenk po směru jízdy, konec ve 3/4 zezadu | PC→C | PAN-L (po směru jízdy) · R→L | 34 → 40 → 36 | 1,7 m, z = -655,5 (7 m od osy) | middle-2.1 0,5–7,0 |
| C | ověřený záběr b02_road: pevná kamera 26 m od osy, švenk za tahačem | PC | PAN-L · R→L | 32 → 38 → 32 | 1,6 m, z = −636 (ověřeno) | middle-2.1 0–7,5 |
| D | nízký tele pohled od konce silnice (druhá varianta 1.1), souprava projede těsně u kamery | C | STAT, tele, nízko · – | 12 | 0,8 m, z = −657,5, x = −80 | middle-1.1 0–9 |

Rizika kamer: **A**: slunce vpravo (jih), jízdní stopa přímá; kamera ve stínu nesmí být; souprava se rozjíždí 4,5 s před záznamem (start x = 90). **B**: oprava QC (middle): o 7 m blíž k silnici (z −655,5) a o 0,3 m výš, širší fov, použít do 7 s; průjezd v čase ≈ 4 s (x kamery 20 = poloha soupravy 60 − 10 m/s · 4 s); odchylka ±0,7 s; keře na jižní straně ověřit. **C**: geometrie převzata z b02_road (ověřená), čas 10:00 místo 18:00 – slunce teď vzadu vpravo. **D**: kamera 5 m od osy: souprava proletí kolem v čase ≈ 14 s (mimo použitou část); Z4 – tráva v popředí do 1 m.

### Blok 2: Dvůr farmy a štěrková cesta: film mini

#### `mini-cesta`

- **Pokrývá:** mini-3.1. **Místo a čas:** CESTA (štěrková cesta z = 172,5 ke stodole, ověřeno b03), 10:10.
- **Akce:** Souprava (JD 3650 + Mini, složený) jede z x = −655 na západ k x = −830 rychlostí 25 km/h po cestě z = 172,5; záznam 3,5 s po rozjezdu.
- **Izolace:** isolate keep=mini props vehicles radius 400.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** plot nebo keř mezi kamerou a soupravou, slunce (B), nedeterministická jízda.
- **Ověřit průzkumem:** pozice C (−745, 168) a B (sever, 26 m od cesty): volné, mimo plot/keře.
- **Soubory:** `scenes/mini-cesta.akce.json`, `mini-cesta.kamA.json`, `mini-cesta.kamB.json`, `mini-cesta.kamC.json`, `mini-cesta.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | ověřený tracking z jihu (b03_gravel): kamera 25–28 m od cesty, stodola v pozadí | PC | TRK (camFollow) · R→L | 34 → 31 | 1,7–1,8 m, 24 → 20 m vlevo | mini-3.1 0,5–7,0 |
| B | tracking ze severní strany (scénář: L→R), proti slunci, jen záloha | PC | TRK (camFollow) · L→R | 34 → 31 | 1,6–1,8 m, 31 → 29 m vpravo (sever) | mini-3.1 0,5–9,5 |
| C | tele zepředu ze západu, souprava se blíží a projede, kamera ji sleduje | C | STAT + sledování cílem · – | 24 → 18 | 1,4 m, x = −751, z = 164 | mini-3.1 1,0–9,0 |
| D | zezadu vysoko, sledování soupravy do dálky (FOL) | PC | FOL · – | 40 | 4 m, 16 m za soupravou | mini-3.1 0,5–9,5 |

Rizika kamer: **A**: oprava QC: konec trajektorie už nezajíždí do porostu (sorgo od ≈ 25 m od cesty), použít jen 0,5–7 s; cizí stroje na dvoře u stodoly jsou v prvních sekundách v záběru (isolate radius 400); ověřit snímkem. **B**: oprava QC: začátek o 5 m dál od plotu a výš (plot v 0–1,5 s); protisvětlo (slunce vpředu vlevo), strana vleku ve stínu – čas je společný pro akci; ověřit snímkem. **C**: oprava QC: o 6 m dál od stěny stodoly a 8,5 m od osy cesty, fov se rozšiřuje (22 → 30), aby se tahač neřízl; použít do 9 s; ověřit snímkem. **D**: záběr z odjezdu – v zorném poli stodola a sila jen občas.

#### `mini-dvur-prijezd`

- **Pokrývá:** mini-3.2. **Místo a čas:** DVŮR (−690, 140), 10:10.
- **Akce:** Souprava vjede z x = −735 na dvůr k bodu (−690, 140) rychlostí 14 km/h a zastaví (radius 2); nikdo nevystupuje. Konečná poloha = FARM_SET (b04).
- **Izolace:** isolate keep=mini props vehicles radius 400.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** stodola, stromy, nedeterministická brzdná dráha (±2 m).
- **Ověřit průzkumem:** start (−735, 140) a trasa po z = 140 jsou průjezdné (c61/c62 používaly mlýnek na (−740…−748, 150…158)).
- **Soubory:** `scenes/mini-dvur-prijezd.akce.json`, `mini-dvur-prijezd.kamA.json`, `mini-dvur-prijezd.kamB.json`, `mini-dvur-prijezd.kamC.json`, `mini-dvur-prijezd.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | nízko od východu proti jízdě: souprava vjede na dvůr a zabrzdí | PC | STAT (nad zábradlím) · – | 36 | 1,7 m, (−666, 145) | mini-3.2 1,0–13,0 |
| B | z jihu od stodoly: souprava projede zleva doprava a zastaví (sluneční strana) | PC | STAT + sledování cílem · L→R | 30 → 26 | 0,9 m, (−706, 160) | mini-3.2 1,0–13,0 |
| C | tele z dálky od východu, komprese perspektivy | C | STAT, tele · – | 18 | 1,8 m, (−640, 137) | mini-3.2 1,0–13,0 |
| D | vyvýšený boční pohled z jihovýchodu | PC | STAT · – | 34 | 2,8 m, (−680, 170) | mini-3.2 1,0–13,0 |

Rizika kamer: **A**: oprava QC: výš nad zábradlí a žlab (y 1,7); ikony hotspotů vypnout ve hře (markers_off.lua); kamera mimo dráhu soupravy; ověřit snímkem. **B**: oprava QC: kamera sleduje soupravu od první sekundy (dřív prázdný dvůr 7 s) a užší fov, souprava je větší. **C**: oprava QC: o 15 m na sever od pastviny (krávy, plot), na štěrk, y 1,8; ověřit snímkem (stromy ve výhledu?). **D**: kamera blízko stodoly: Z4 (zeď do 1 m).

#### `mini-rozlozeni`

- **Pokrývá:** mini-4.1. **Místo a čas:** DVŮR (−690, 140), yaw 90, pravý bok k jihu, 10:20.
- **Akce:** Mini + JD 3650 stojí složený na FARM_SET; t = 2 s `fold unfold` (12 s animace: bedna, panely, dron), +13 s dojezd. Mini: bez žebříku a plachet.
- **Izolace:** isolate keep=mini props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z7 dron mimo plán (dron musí být složený při startu), sluneční protisvětlo u A.
- **Ověřit průzkumem:** doba animace 12 s; po `fold unfold` stojí dron na heliportu a vrtule nejsou roztočené.
- **Soubory:** `scenes/mini-rozlozeni.akce.json`, `mini-rozlozeni.kamA.json`, `mini-rozlozeni.kamB.json`, `mini-rozlozeni.kamC.json`, `mini-rozlozeni.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | oblet po směru hodin od levého zadního rohu k levému boku (sever) | C | ORB-CW · CW | 38 → 36 | 1,7 → 2,3 m, r = 9 → 8 m | mini-4.1 2,0–14,0 |
| B | oblet proti směru hodin od pravého zadního rohu k pravému boku (jih, slunce vzadu) | C | ORB-CCW · CCW | 38 → 36 | 1,5 → 2,0 m, r = 8,5 → 8 m | mini-4.1 2,0–14,0 |
| C | pevný záběr zezadu: plošina se rozkládá směrem ke kameře | C | STAT · – | 34 | 1,5 m, 9,5 m za vlekem | mini-4.1 2,0–14,0 |
| D | boční jízda podél pravého boku zepředu dozadu s mírným jeřábem nahoru | PC | TRK + JIB-U · R→L | 36 | 0,9 → 2,8 m, 8 m od osy | mini-4.1 2,0–14,0 |

Rizika kamer: **A**: protisvětlo na severní straně (slunce za vlekem), tahač v záběru na konci orbitu. **B**: kamera prochází jižní stranou dvora: stodola 40 m jižně, volno ověřit. **C**: heliport a dron mohou být zakryty zadním panelem v první sekundě. **D**: oprava QC: cíl je teď v souřadnicích vleku (tat=M; dřív světový bod, kamera mířila na pastvinu); kamera sleduje cíl před plošinou, pohyb rovnoběžný s vozem; Z4 – jižní trávník.

#### `mini-detaily`

- **Pokrývá:** mini-4.2, mini-4.3, mini-4.4, mini-4.5, mini-4.6. **Místo a čas:** DVŮR (−690, 140), rozložený Mini, 10:22.
- **Akce:** Stojící rozložený Mini; žádná animace, jen pohyb kamery. Okno pro každý detail 5,5 s (užito 3,5 s), t = 2,0 / 7,5 / 13,0 / 18,5 / 24,0 s.
- **Izolace:** isolate keep=mini props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z8 odlesk, kabel zakrývá sloty (D3), hadice na navíječi (D5).
- **Ověřit průzkumem:** souřadnice cílů D1–D5 podle uzlů (kap. 5 scénáře) – kontrolní snímek před natáčením; D3: je truhla po rozložení otevřená?.
- **Soubory:** `scenes/mini-detaily.akce.json`, `mini-detaily.kamA.json`, `mini-detaily.kamB.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | pět detailů v pořadí scénáře: NAJ heliport, TILT-U centrála, STAT šachta, TRK L→R nádrž, ODJ navíječ | D | NAJ / TILT-U / STAT / TRK L→R / ODJ · různé | 30–38 | 0,35–2,4 m, 1–4 m od dílů | mini-4.2 2,0–7,5; mini-4.3 7,5–13,0; mini-4.4 13,0–18,5; mini-4.5 18,5–24,0; mini-4.6 24,0–29,5 |
| B | druhá varianta: jiné strany a opačný pohyb (STAT-orbit heliport, TILT-D, NAJ šachta, TRK R→L, NAJ navíječ) | D | variace A · opačné | 30–36 | 0,5–1,9 m | mini-4.2 2,0–7,5; mini-4.3 7,5–13,0; mini-4.4 13,0–18,5; mini-4.5 18,5–24,0; mini-4.6 24,0–29,5 |

Rizika kamer: **A**: polohy dílů počítány z i3d (rotace nadřazených uzlů zanedbána) – ověřit snímkem; 4.4: víko truhly po rozložení otevřené?. **B**: levá strana (centrála, šachta) je proti slunci – stín; ověřit expozici.

#### `mini-kanystr`

- **Pokrývá:** mini-5.1, mini-5.2. **Místo a čas:** DVŮR (−690, 140), rozložený Mini, 10:30.
- **Akce:** t = 2 s otevře se bedna (`toolboxSet open`), t ≈ 4,5 s `canisterPour from=box slot=1` (zvedne 2 s, naklopí 2 s, lije 6 s, vrátí), police naplněny předem; hrdlo koncentrátu prázdné.
- **Izolace:** isolate keep=mini props vehicles (smaže i cizí kanystry).
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z9 neviditelná ruka, Z2 cizí kanystry (hnojivo, nafta) na polici – police jen herbicid?.
- **Ověřit průzkumem:** slot 1 leží v pravé bedně nejblíž hrdlu (toolboxCanister1 = (−0,70; 0,76; 1,23)); police obsahují jen herbicid (jinak štítky jiných látek v záběru).
- **Soubory:** `scenes/mini-kanystr.akce.json`, `mini-kanystr.kamA.json`, `mini-kanystr.kamB.json`, `mini-kanystr.kamC.json`, `mini-kanystr.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | najetí k pravé bedně (štítek ≥ 1 s), pak švenk k hrdlu koncentrátové nádrže | PC→D | NAJ → PAN-R · – | 40 → 28 → 34 | 1,5 → 1,2 m, 2,2–4,8 m od bedny | mini-5.1 0,0–7,0; mini-5.2 7,5–14,5 |
| B | vyvýšený pevný pohled zepředu zprava: bedna i hrdlo v jednom záběru | PC | STAT · – | 28 | 2,6 m, (−3,2; 4,2) | mini-5.1 0,0–7,0; mini-5.2 7,5–14,5 |
| C | nízká pevná kamera u hrdla: kanystr se naklání a koncentrát se vlévá | D | STAT nízko · – | 36 | 1,2 m, (−2,5; 4,0) | mini-5.2 7,5–14,5 |
| D | detail štítku: blízký pomalý nájezd na police, pak statika u hrdla | D | NAJ → STAT · – | 28 → 26 / 30 | 1,55–1,7 m, 1,6 m od police | mini-5.1 0,0–7,0; mini-5.2 7,5–14,5 |

Rizika kamer: **A**: oprava QC: 5.1 shora do otevřené bedny (cíl na kanystr ve slotu 1, ne na logo), 5.2 z výšky 2,5–2,7 m na kanystr nad hrdlem (spodek skrytý, odstup ≥ 2 m); ověřit snímkem (víko bedny). **B**: oprava QC: fov 40 → 28 a cíl mezi bednou a hrdlem (štítek kanystru čitelný); tahač v pozadí, kabina nesmí zakrývat; stín od JD 3650. **C**: oprava QC: o 1 m dál a výš (y 1,2), kanystr není na okraji; jen 5.2; Z9: spodek kanystru z nízka – kanystr nese neviditelná ruka. **D**: oprava QC: 5.1 šikmo shora do otevřené bedny na kanystr ve slotu 1 (dřív logo bedny); štítek herbicidu: čitelnost ověřit snímkem.

#### `mini-planovac`

- **Pokrývá:** mini-6.1, mini-6.2, mini-6.3. **Místo a čas:** DVŮR (−690, 140), plánovač (celoobrazovkový), 10:40.
- **Akce:** t = 1 s `screenWake` (displej se rozsvítí, předtím uspán), t = 6 s `ui plannerOpen`, výběr pole 4, počáteční pohled mapy (−690, 190) zoom 1,8; t = 15,5 s stránka 2 (karta).
- **Izolace:** isolate keep=mini park=260,-665 (ikony cizích soupravy mimo okno mapy), relayRemove.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z5 kurzor/bubliny, ikony cizích vleků v mapě; pole 4 musí být v dosahu rádia (S 300 m: 85 m ✓).
- **Ověřit průzkumem:** plannerPage 2 = karta plánu (a 3 = Let?); screenWake probudí displej viditelně; cizí ikony v okně mapy při zoom 1,8.
- **Soubory:** `scenes/mini-planovac.akce.json`, `mini-planovac.kamA.json`, `mini-planovac.kamB.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | displej na vleku (STAT), mapa: plynulé přiblížení na pole 4 (MAPA+), karta plánu | D / UI | STAT → MAPA+ → STAT · – | 32 (svět) | 1,2 m, 1,5 m od displeje | mini-6.1 0,5–5,5; mini-6.2 8,0–15,0; mini-6.3 15,5–21,5 |
| B | nájezd na displej (NAJ), mapa: výběr přeskočí z pole 3 na pole 4 se zoomem, karta bez přepnutí na Let | D / UI | NAJ → skok výběru + MAPA+ → STAT · – | 32 → 28 (svět) | 1,1–1,5 m | mini-6.1 0,5–5,5; mini-6.2 8,0–15,0; mini-6.3 15,5–21,5 |

Rizika kamer: **A**: displej může při probuzení bliknout; kurzor myši v záznamu není, hover vypnut (plannerHover off). **B**: stránka karty (plannerPage 2) – ověřit, že je to karta plánu pole; hlášky „Cizí pole“ nesmí být.

#### `mini-let`

- **Pokrývá:** mini-7.1, mini-7.2, mini-7.3, mini-7.4. **Místo a čas:** DVŮR → pole 4 (−697, 235), 10:45.
- **Akce:** t = 2 s `startFlight` (pole 4, herbicid, bez větru), okno 7.1 do t = 9 s, potom `waitDrone spraying` (ack, čas nedeterministický), značky w1/w2/w3 po 6,5 s = okna 7.2/7.3/7.4, nakonec `returnHome`.
- **Izolace:** isolate keep=mini props vehicles radius 400.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z7 dron mimo plán (7.1: kamera musí vidět vzlet), stromy v ose stoupání, vítr (windOff), nedeterministický začátek postřiku (±0,3 s po příkazu, proměnný čas příletu).
- **Ověřit průzkumem:** jméno fillType herbicidu (HERBICIDE) a že dron stříká bílomodrou mlhu; pole 4: vlastnictví (own) a dosah; směr řádků pole 4 pro statický záběr 7.4 (kalibrační běh `trace on`).
- **Soubory:** `scenes/mini-let.akce.json`, `mini-let.kamA.json`, `mini-let.kamB.json`, `mini-let.kamC.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | 7.1 jeřáb nahoru u plošiny, 7.2 FOL zezadu, 7.3 TOP nad dronem, 7.4 boční tracking zleva | C / PC | JIB-U → FOL → TOP → TRK · R→L (7.4) | 38 → 32 / 34 / 40 / 32 | 1,3 → 5,8 m; FOL 2,6 m; TOP 27 m; TRK 1,5 m | mini-7.1 t=2 +0–t=2 +7; mini-7.2 w1 +0–w1 +6,5; mini-7.3 w2 +0–w2 +6,5; mini-7.4 w3 +0–w3 +6,5 |
| B | 7.1 pevná kamera zpředu zprava (TILT), 7.2 FOL vysoko, 7.3 TOP statický nad polem, 7.4 tracking zprava | C / PC | STAT → FOL → TOP statický → TRK · L→R (7.4) | 40 → 34 / 36 / 32 / 32 | 1,2 m; FOL 7 m; TOP 45 m nad polem (sleduje dron); TRK 1,5 m | mini-7.1 t=2 +0–t=2 +7; mini-7.2 w1 +0–w1 +6,5; mini-7.3 w2 +0–w2 +6,5; mini-7.4 w3 +0–w3 +6,5 |
| C | 7.1 jeřáb zleva zezadu, 7.2 FOL zepředu (3/4), 7.3 TOP vysoko, 7.4 FOL nízko zezadu (záloha TRK) | C / PC | JIB-U → FOL (čelo) → TOP → FOL nízko · – | 36 / 34 / 28 / 36 | 1,0 → 5,5 m; FOL 2 m; TOP 42 m | mini-7.1 t=2 +0–t=2 +7; mini-7.2 w1 +0–w1 +6,5; mini-7.3 w2 +0–w2 +6,5; mini-7.4 w3 +0–w3 +6,5 |

Rizika kamer: **A**: 7.1: stromy v ose stoupání (pojistka dronu, STATUS_OBSTACLE); 7.4 závisí na směru řádků – nutný kalibrační běh s `trace on`. **B**: oprava QC: 7.3 z 95 m (dron pár pixelů) → 45 m nad polem, fov 32, cíl sleduje dron (tat=DR); cizí stroje pod přístřeškem – isolate radius 400. **C**: oprava QC: 7.2 kamera víc do osy letu (ox 4,5 → 1,5) a fov 34 → 40, dron nemá utíkat vlevo; FOL zepředu: držet 9 m před dronem (tau 0,9).

#### `mini-navrat-servis`

- **Pokrývá:** mini-7.5, mini-7.6, mini-7.7. **Místo a čas:** DVŮR (−690, 140), 11:00.
- **Akce:** Hlava: `startFlight`, po vzletu +2,5 s `droneSet battery 0,2 tank 1,5` (dron se sám vrací), čeká na `near 28 m`; záznam začíná při příletu. Dále `waitDrone servicing` (přistání), značka servicing, servis 14 s (baterie 5 s, nádrž ≈ 20 s).
- **Izolace:** isolate keep=mini props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z7 dron mimo záběr při přistání, nedeterministický čas přistání (±1 s), kamera 1,5 m od dronu.
- **Ověřit průzkumem:** `waitDrone near` 28 m dává dost času pro 7.5; poloha šachty baterií vůči dronu v kamerách B, D.
- **Soubory:** `scenes/mini-navrat-servis.akce.json`, `mini-navrat-servis.kamA.json`, `mini-navrat-servis.kamB.json`, `mini-navrat-servis.kamC.json`, `mini-navrat-servis.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | 7.5 tele pevně na přistání, 7.6 oblet proti směru hodin kolem dronu na desce | PC | STAT tele → ORB-CCW · CCW | 22 / 40 | 1,4 m; orbit 2,2 → 1,8 m, r = 6 → 5 | mini-7.5 0,0–7,0; mini-7.6 servicing +0–servicing +12 |
| B | 7.5 nízká statika zepředu zprava, 7.7 detail výměny baterie (nájezd k šachtě) | PC / D | STAT → NAJ · – | 34 / 32 → 28 | 0,9 m; 1,6 → 1,5 m | mini-7.5 0,0–7,0; mini-7.7 servicing +0–servicing +10 |
| C | 7.5 FOL za sestupem dronu, 7.6 oblet po směru hodin (opačný směr než A) | PC | FOL → NAJ na truhlu · – | 34 / 30 → 26 | 2,4 m; 1,6 → 1,4 m, 3–4 m od truhly | mini-7.5 0,0–7,0; mini-7.6 servicing +0–servicing +12 |
| D | 7.5 shora zleva, 7.7 detail dronu a hadice zblízka (druhá varianta) | PC / D | STAT → NAJ → přejezd na navíječ · – | 34 / 28 → 30 | 3,0 m; 0,7–1,45 m | mini-7.5 0,0–7,0; mini-7.7 servicing +0–servicing +10 |

Rizika kamer: **A**: 7.5: dron může zmizet ze záběru (konec přiblížení), v tele pozor na plot; hadice se napojuje vpravo od plošiny. **B**: oprava QC: 7.7 míří na dron na heliportu (dřív na šachtu vlevo, dron mimo záběr), kamera zleva zepředu 3,3 m od dronu, y 1,5–1,6, fov 32 → 28; baterie se vyměňuje 5 s; ověřit snímkem. **C**: oprava QC: místo orbitu pohled těsně na truhlu s bateriemi (šachta x +0,5…+0,72, z 1,57) zleva zepředu, fov 30 → 26; výměna baterie se čte; ověřit snímkem (víko truhly, kabel). **D**: oprava QC: 7.7 odsun o 0,5 m a cíl o 0,25 m výš (vejde se baterie nad dronem), od 5,5 s plynulý přejezd na navíječ s hadicí (doplnění nádrže); mixované vztažné soustavy dron → vlek v klíčích; ověřit snímkem.

#### `mini-slozeni-odjezd`

- **Pokrývá:** mini-8.1, mini-8.2. **Místo a čas:** DVŮR → odjezd na východ (z = 140), 11:30.
- **Akce:** t = 2 s `fold fold` (složení bedny, panelů a dronu, 12 s), t = 15 s `driveTo` (−560, 140) rychlostí 20 km/h, 9 s jízdy.
- **Izolace:** isolate keep=mini props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z7 roztočená vrtule u složeného vleku, trasa odjezdu (plot, pole 1 na sever).
- **Ověřit průzkumem:** trasa odjezdu z dvora (z = 140 → x = −560).
- **Soubory:** `scenes/mini-slozeni-odjezd.akce.json`, `mini-slozeni-odjezd.kamA.json`, `mini-slozeni-odjezd.kamB.json`, `mini-slozeni-odjezd.kamC.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | 8.1 jeřáb dolů nad složením, 8.2 pevný tele zezadu za odjíždějící soupravou | C | JIB-D → STAT tele + sledování · – | 36 → 34 / 20 → 14 | 5,5 → 1,5 m; 1,4 m | mini-8.1 2,0–14,0; mini-8.2 15,0–24,0 |
| B | 8.1 oblet proti směru hodin, 8.2 tele ze severu/jihu se sledováním cíle (odjezd L→R) | C | ORB-CCW → STAT + sledování · CCW / L→R | 38 / 20 | 1,8 m; 1,3 m | mini-8.1 2,0–14,0; mini-8.2 15,0–24,0 |
| C | 8.1 pevný nízký záběr zezadu (panely se skládají), 8.2 FOL za soupravou | C / PC | STAT → FOL · – | 36 / 40 | 1,2 m; 2,8 m | mini-8.1 2,0–14,0; mini-8.2 15,0–24,0 |

Rizika kamer: **A**: oprava QC: 8.2 sleduje soupravu (tat=JD), tahač už není ořezaný vlevo; trasa odjezdu (z = 140 na východ) není ověřená; tele pohled přes plot?. **B**: oprava QC: kamera o 7 m jižněji na štěrkové cestě (z = 172, bez ohrady), fov 20 → 16; souprava míjí kameru ve vzdálenosti ≈ 32 m; ověřit snímkem. **C**: FOL po `fold` s kamerou vázanou na tahač: souprava se rozjíždí ihned – kamera musí být 14 m za vlekem při startu.

### Blok 3: Poloostrov u velké vody (POLO): film middle

#### `middle-cesta`

- **Pokrývá:** middle-3.1. **Místo a čas:** cesta k POLO (z = 455, x od -735), 11:10.
- **Akce:** Pickup + Middle (složený) jede na východ z x = -735 k x = -675 (25 km/h) po trase z = 455; záznam 3 s po rozjezdu.
- **Izolace:** isolate keep=middle props vehicles radius 400.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** driveTo mode=line jede přímo (ne po cestě), potřeba přímý bezstromový úsek ≥ 60 m.
- **Ověřit průzkumem:** přímý průjezdný úsek z = 455 od x = -735 do -675 (stromy, rákos); umístění kamer C, B (voda jižně).
- **Soubory:** `scenes/middle-cesta.akce.json`, `middle-cesta.kamA.json`, `middle-cesta.kamB.json`, `middle-cesta.kamC.json`, `middle-cesta.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | tracking ze severu (scénář R→L): pickup s vlekem jede mezi loukami a stromy k poloostrovu | PC | TRK (camFollow) · R→L | 38 → 35 | 1,2–1,4 m, 14 m od jízdy (jih) | middle-3.1 0,5–9,0 |
| B | tracking z jihu (slunce vzadu, L→R) – záloha | PC | TRK (camFollow) vysoko z jihu · R→L | 32 → 30 | 3,0–3,2 m, 17 m od jízdy (jih) | middle-3.1 0,5–9,0 |
| C | tele zepředu od východu, souprava se blíží po louce | C | STAT + sledování cílem · – | 22 → 30 | 1,5 m, (−735, 184), 11,5 m jižně od cesty | middle-3.1 1,0–9,5 |
| D | vysoko zezadu, souprava se vzdaluje k poloostrovu (FOL) | PC | FOL · – | 40 | 4 m, 16 m za soupravou | middle-3.1 0,5–9,5 |

Rizika kamer: **A**: oprava QC: cíl o 1,5 m dopředu a fov 34 → 38 (pickup se nesmí ořezávat vpravo); větve nesmí zakrýt vlek. **B**: oprava QC: severní strana (+14 m) vedla keři a stromy (kamera uvnitř listí 2–5 s), proto z jihu (strana A je prokazatelně čistá louka), výš (y 3) a dál (17 m), s předstihem; sorgo od ≈ 25 m od cesty – ověřit snímkem. **C**: oprava QC: kamera na jižní straně cesty blíž k trase (dřív 5 m severně od cesty u stodoly, cizí kombajn), souprava se blíží z dálky a fov se rozšiřuje; ověřit snímkem. **D**: stromy nad kamerou.

#### `middle-polo-prijezd`

- **Pokrývá:** middle-3.2. **Místo a čas:** POLO (-625, 455), voda jižně, 11:15.
- **Akce:** Souprava (pickup + Middle) vjede z x = -670 na louku a zastaví v bodě (-625, 455), yaw 90 (pravý bok k jihu a k vodě).
- **Izolace:** isolate keep=middle props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** hráč, zvěř, pumpa v záběru nesmí být; rákos.
- **Ověřit průzkumem:** POLO: místo (-625, 455) je rovné a volné, voda a rákos jižně od z ≈ 465; kamery A–D stojí na souši.
- **Soubory:** `scenes/middle-polo-prijezd.akce.json`, `middle-polo-prijezd.kamA.json`, `middle-polo-prijezd.kamB.json`, `middle-polo-prijezd.kamC.json`, `middle-polo-prijezd.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | ze severu: couvání kamery odhalí hladinu a rákos za soupravou (protisvětlo) | PC→C | ODJ (statické klíče, dráha za soupravou) · – | 32 → 28 | 3,8 → 4,8 m, (-641, 431) → (-645, 424) | middle-3.2 6,0–13,0 |
| B | z hladiny (kamera 5 m nad vodou) STAT: souprava dojede a zastaví na louce | PC | STAT · – | 32 | 2,6 m, (-642, 447), na břehu 8 m severně od trasy | middle-3.2 1,0–14,0 |
| C | tele od západu proti jízdě, komprese | C | STAT tele · – | 22 | 2,0 m, (-610, 449) | middle-3.2 1,0–14,0 |
| D | vyvýšený široký záběr z jihozápadu s vodou v pozadí (hledí k severovýchodu) | C | STAT + pomalý nájezd (fov) · – | 36 → 26 | 5,0 m, (-660, 445) – ověřená poloha | middle-3.2 1,0–14,0 |

Rizika kamer: **A**: oprava QC: kamera o 6 m na západ (strom a keř vlevo v ose) a z 6 na 3,8 m (větev v 14 s), použít do 13 s; ověřit snímkem. **B**: oprava QC: kamera z hladiny (rákos mezi kamerou a vlekem) přesunuta na břeh poloostrova; rákos nesmí být v záběru, ověřit snímkem. **C**: oprava QC: kamera z rákosu a keře (−605; 462) na sever k (−610; 449), y 2,0; souprava jede proti kameře a zastaví 15 m před ní; ověřit snímkem. **D**: oprava QC: souprava v 4–15 s miniaturní → fov 36 → 26 (poloha beze změny); keř vlevo částečně zakrývá pickup, ověřit snímkem.

#### `middle-rozlozeni`

- **Pokrývá:** middle-4.1. **Místo a čas:** POLO, yaw 90, 11:20.
- **Akce:** Middle + pickup složený; t = 2 s `fold unfold` (plachty, žebřík, stožár, dron na horní plošině; ≈ 10 s), nodeVis zobrazí anténu a GPS před rozložením.
- **Izolace:** isolate keep=middle props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z7 dron na plošině se rozkládá až ve scéně; voda a stromy.
- **Ověřit průzkumem:** doba rozložení ≈ 10 s (foldLadder 5 s + dron); stožár se při rozložení vysune viditelně (O10).
- **Soubory:** `scenes/middle-rozlozeni.akce.json`, `middle-rozlozeni.kamA.json`, `middle-rozlozeni.kamB.json`, `middle-rozlozeni.kamC.json`, `middle-rozlozeni.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | oblet proti směru hodin od pravého zadního rohu k pravému boku (žebřík, jih, voda) | C | ORB-CCW · CCW | 40 → 38 | 3,2 → 3,6 m, r = 8,5 → 8 m | middle-4.1 2,0–12,0 |
| B | oblet po směru hodin od levého zadního rohu k levému boku (sever) | C | ORB-CW · CW | 38 → 36 | 1,6 → 2,4 m, r = 9 → 8,5 m | middle-4.1 2,0–12,0 |
| C | pevný záběr zezadu: plachty, žebřík a stožár vyrůstají nad vlekem | C | STAT · – | 36 | 3,4 m, 10 m od pravého boku (zadní třetina) | middle-4.1 2,0–12,0 |
| D | boční jízda podél pravého boku zepředu dozadu s jeřábem nahoru | PC | TRK + JIB-U · R→L | 36 | 2,8 → 4,0 m, 9 m od osy | middle-4.1 2,0–12,0 |

Rizika kamer: **A**: oprava QC: oblet nad pásem rákosu (y ≥ 3,2 m od začátku, rákos ≈ 2 m); cíl ly 1,8; ověřit snímkem. **B**: oprava QC: oblet končí dřív (u středu levého boku místo předu), aby keř u pickupu nevstoupil do záběru (dřív po 8 s); protisvětlo. **C**: oprava QC: z osy za vlekem na bok (pravý bok = jih, strana s žebříkem), výška 3,4 m nad pás rákosu; stožár může opustit horní okraj (4,6 m výška); ověřit snímkem. **D**: oprava QC: jízda vedla rákosem (y 1,0–1,8, pálky přes obraz) → od t = 0 ve výšce 2,8 m nad rákosem (≈ 2 m), 9 m od osy; ověřit snímkem.

#### `middle-detaily`

- **Pokrývá:** middle-4.2, middle-4.3, middle-4.4, middle-4.5, middle-4.6. **Místo a čas:** POLO, rozložený Middle, 11:22.
- **Akce:** Stojící rozložený Middle; jen pohyb kamery; okna 5,5 s od t = 2,0 / 7,5 / 13,0 / 18,5 / 24,0 s.
- **Izolace:** isolate keep=middle props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z8 odlesk; hadice na ventilu; stožár vysunutý (jen 4.6).
- **Ověřit průzkumem:** souřadnice cílů D1–D5 (kap. 5 scénáře) – kontrolní snímek; D2: plachta na pravém boku (TarpTrack_R) je rozvinutá.
- **Soubory:** `scenes/middle-detaily.akce.json`, `middle-detaily.kamA.json`, `middle-detaily.kamB.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | TILT-U žebřík, TRK L→R plachta, NAJ truhla s vzpěrami, STAT nádrž a ventil, JIB-U stožár | D | TILT-U / TRK L→R / NAJ / STAT / JIB-U · různé | 30–38 | 0,6–4,2 m | middle-4.2 2,0–7,5; middle-4.3 7,5–13,0; middle-4.4 13,0–18,5; middle-4.5 18,5–24,0; middle-4.6 24,0–29,5 |
| B | variace: NAJ žebřík zepředu, TRK R→L plachta, STAT shora truhla, NAJ nádrž, TILT-U stožár z paluby | D | NAJ / TRK R→L / STAT / NAJ / TILT-U · opačné | 30–36 | 1,2–3,6 m | middle-4.2 2,0–7,5; middle-4.3 7,5–13,0; middle-4.4 13,0–18,5; middle-4.5 18,5–24,0; middle-4.6 24,0–29,5 |

Rizika kamer: **A**: levá strana (truhla) ve stínu; stožár vystupuje nad záběr (ověřit rozsah 4,4 m). **B**: oprava QC: 4.3 začíná až za pickupem (keř v korbě v 8–9 s mimo záběr), 4.4 o 0,5 m výš a vpravo (víko nezakrývá sloty); kamera 1,8 m od stožáru: Z4 – dron na plošině nesmí být v záběru při TILT-U; ověřit snímkem.

#### `middle-kanystr`

- **Pokrývá:** middle-5.1, middle-5.2. **Místo a čas:** POLO, rozložený Middle, 11:30.
- **Akce:** t = 2 s otevře se skříň (`toolboxSet open`), t = 4,5 s `canisterPour from=box slot=1` fertilizer; police předem naplněny.
- **Izolace:** isolate keep=middle props vehicles (smaže cizí kanystry).
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z9 neviditelná ruka, Z2 kanystry herbicidu a nafty na polici.
- **Ověřit průzkumem:** trajektorie kanystru z police 1 (zadní skříň) k hrdlu na pravém boku (průchod karoserií?); police obsahují jen hnojivo.
- **Soubory:** `scenes/middle-kanystr.akce.json`, `middle-kanystr.kamA.json`, `middle-kanystr.kamB.json`, `middle-kanystr.kamC.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | ověřená dráha c33: zezadu k roletě skříně, pak podél pravého boku k hrdlu | PC→D | NAJ ke štítku → NAJ k hrdlu · – | 38 → 26 → 34 | 1,0 m; 2,3 → 2,6 m | middle-5.1 0,0–7,0; middle-5.2 7,5–15,0 |
| B | 5.1 pevně zezadu na skříň, 5.2 nízká pevná kamera u hrdla | PC / D | NAJ → STAT · – | 34 → 26 / 30 | 1,5 → 1,35 m; 2,4 m | middle-5.1 0,0–7,0; middle-5.2 7,5–15,0 |
| C | detail štítku na polici a pak shora na vlévání | D | NAJ → STAT · – | 26 → 34 | 1,3 m; 2,6 m | middle-5.1 0,0–7,0; middle-5.2 7,5–15,0 |

Rizika kamer: **A**: oprava QC: 5.1 nájezd těsně ke štítku kanystru ve slotu 1 (−0,75; 0,74; −1,95; ≥ 1 s čitelný, fov 26), 5.2 z výšky 2,3–2,6 m, spodek kanystru skrytý; roleta jede nahoru do pouzdra; ověřit snímkem. **B**: oprava QC: 5.1 pomalý nájezd na štítek (fov 34 → 26, cíl na kanystr), 5.2 výš (y 2,4) a fov 30, aby nebyl vidět spodek kanystru; ověřit snímkem. **C**: štítek hnojiva čitelný z fov 26? (barva podobná herbicidu – O15).

#### `middle-planovac`

- **Pokrývá:** middle-6.1, middle-6.2, middle-6.3. **Místo a čas:** POLO, plánovač, 11:40.
- **Akce:** t = 1 s `screenWake`, t = 6 s plánovač (pole 91), počáteční pohled (−700, 620) zoom 2,6; t = 15,5 s stránka 2 (karta).
- **Izolace:** isolate keep=middle (cizí ikony mimo okno mapy), relayRemove.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z5 hlášky; pole mimo dosah → relé (ui relaySpawn).
- **Ověřit průzkumem:** ID pole jižně od poloostrova = 91 (střed (−710, 701), 4,23 ha), vlastnictví a dosah; plannerPage 2 = karta plánu.
- **Soubory:** `scenes/middle-planovac.akce.json`, `middle-planovac.kamA.json`, `middle-planovac.kamB.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | displej (NAJ), mapa: pole jižně od poloostrova, plynulé oddálení na kruh dosahu (MAPA−) | D / UI | NAJ → MAPA− → STAT · – | 32 → 28 (svět) | 1,5 m, 3 m od displeje | middle-6.1 0,5–5,5; middle-6.2 8,0–15,0; middle-6.3 15,5–21,5 |
| B | displej pevně z odstupu, mapa: výběr pole 91 se zoomem, pak oddálení | D / UI | STAT → skok výběru + MAPA− · – | 30 (svět) | 1,6 m, 4 m | middle-6.1 0,5–5,5; middle-6.2 8,0–15,0; middle-6.3 15,5–21,5 |

Rizika kamer: **A**: displej je na levém boku (sever) – ve stínu a proti slunci; kurzor není vidět. **B**: pole 91 musí být do dosahu 300 m od vleku (264 m).

#### `middle-let`

- **Pokrývá:** middle-7.0, middle-7.1, middle-7.2, middle-7.3, middle-7.4. **Místo a čas:** POLO → pole 91 (−710, 701), 11:45.
- **Akce:** t = 2 s dron na plošině (7.0, 3 s statika), t = 6,5 s `startFlight` (okno 7.1 do t = 13,5), potom `waitDrone spraying` (let ≈ 260 m: ≈ 35–45 s), značky w1/w2/w3 po 6,5 s, `returnHome`.
- **Izolace:** isolate keep=middle props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z7 dron v zeleni, koruny stromů v ose stoupání (pojistka dronu), vítr, let 260 m přesahuje dosah při malé baterii.
- **Ověřit průzkumem:** volný svislý sloupec nad plošinou a osa stoupání ≥ 25 m (O5); jméno LIQUIDFERTILIZER a pole 91 vlastnitelné (own); palubní kamera: osa uzlu dronu.
- **Soubory:** `scenes/middle-let.akce.json`, `middle-let.kamA.json`, `middle-let.kamB.json`, `middle-let.kamC.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | 7.0 NAJ na dron, 7.1 pevná kamera se naklání za stoupáním, 7.2 FOL, 7.3 TOP nad dronem, 7.4 boční tracking | D / C / PC | NAJ → STAT (TILT-U) → FOL → TOP → TRK · R→L (7.4) | 32 → 28 / 36 / 34 / 40 / 32 | 0,45–0,8 m od dronu; 2,6 m (sever, 8 m); 2,6 m; 27 m; 1,5 m | middle-7.0 t=2,0–t=5,0; middle-7.1 start +0–start +7; middle-7.2 w1 +0–w1 +6,5; middle-7.3 w2 +0–w2 +6,5; middle-7.4 w3 +0–w3 +6,5 |
| B | 7.0 NAJ z opačné strany, 7.1 pevná zleva, 7.2 FOL vysoko, 7.3 TOP statický nad polem (cíl na dronu), 7.4 FOL nízko zezadu | D / C / PC | NAJ → STAT → FOL → TOP statický → FOL nízko · – | 30 / 38 / 36 / 36 / 36 | 0,5–0,9 m; 1,0 m; 7 m; 45 m; 1,2 m | middle-7.0 t=2,0–t=5,0; middle-7.1 start +0–start +7; middle-7.2 w1 +0–w1 +6,5; middle-7.3 w2 +0–w2 +6,5; middle-7.4 w3 +0–w3 +6,5 |
| C | 7.0 zepředu, 7.1 jeřáb zleva zezadu, 7.2 FOL zepředu 3/4, 7.3 TOP vysoko, 7.4 tracking zprava | D / C / PC | NAJ → JIB-U → FOL (čelo) → TOP → TRK · L→R (7.4) | 28 / 36 / 34 / 28 / 32 | 0,4–0,7 m; 1,0 → 5,5 m; 2 m; 42 m; 1,5 m | middle-7.0 t=2,0–t=5,0; middle-7.1 start +0–start +7; middle-7.2 w1 +0–w1 +6,5; middle-7.3 w2 +0–w2 +6,5; middle-7.4 w3 +0–w3 +6,5 |

Rizika kamer: **A**: oprava QC: 7.1 stojí na severní straně (−7,5 → +8,5 m od osy, y 2,6 m) – dřív v rákosu jižně od vleku; 7.0: dron stojí (rotory nestojí-li vrtule, čekat); 7.1: koruny nad plošinou; ověřit snímkem. **B**: oprava QC: 7.3 statika 45 m nad polem s cílem na dronu (dřív 100 m vedle dronu); 7.4 palubní kamera selhala → FOL nízko zezadu (záloha TRK jako A/C). **C**: oprava QC: 7.0 nájezd o 0,5 m vpravo (mimo víko truhly), 7.2 ox 4,5 → 2,0, oy 2 → 4 m (větev a remorkér mimo), fov 38; FOL zepředu: držet ≥ 9 m před dronem; pozor na stožár.

#### `middle-navrat-servis`

- **Pokrývá:** middle-7.5, middle-7.6, middle-7.7. **Místo a čas:** POLO, 12:05.
- **Akce:** Hlava: `startFlight`, po vzletu +2,5 s `droneSet battery 0,2 tank 1,5` (dron se vrací), čeká na `near 34 m`; záznam začíná při příletu; `waitDrone servicing`, značka, servis 14 s.
- **Izolace:** isolate keep=middle props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** dron mizí v zeleni, nedeterministický přílet.
- **Ověřit průzkumem:** směr příletu dronu od pole (jih) vůči kamerám A, D.
- **Soubory:** `scenes/middle-navrat-servis.akce.json`, `middle-navrat-servis.kamA.json`, `middle-navrat-servis.kamB.json`, `middle-navrat-servis.kamC.json`, `middle-navrat-servis.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | 7.5 švenk doleva za přilétajícím dronem (PAN-L), 7.6 oblet po směru hodin | PC | PAN-L → ORB-CW · CW | 30 / 40 | 1,5 m; orbit 1,6 → 1,5 m, r = 6,5 → 5,5 | middle-7.5 0,0–7,0; middle-7.6 servicing +0–servicing +12 |
| B | 7.5 vyvýšená statika zleva, 7.7 detail výměny baterie (truhla vlevo vpředu) | PC / D | STAT → NAJ · – | 34 / 36 → 30 | 3,6 m; 3,6 m | middle-7.5 0,0–7,0; middle-7.7 servicing +0–servicing +10 |
| C | 7.5 FOL za sestupem, 7.6 oblet proti směru hodin (opačný směr) | PC | FOL → ORB-CCW · CCW | 34 / 38 | 2,4 m; orbit 1,6 → 1,8 m, r = 5 → 4,2 | middle-7.5 0,0–7,0; middle-7.6 servicing +0–servicing +12 |
| D | 7.5 tele zdálky, 7.7 detail dronu a hadice zblízka | PC / D | STAT tele → ODJ · – | 22 / 28 | 1,6 m; 0,6 m | middle-7.5 0,0–7,0; middle-7.7 servicing +0–servicing +10 |

Rizika kamer: **A**: oprava QC: 7.6 orbit snížen (výška 2,4 → 1,6 m) a cíl níž na truhlu s hadicí (ly 0,2); keř za pickupem zůstává; dron přilétá od jihu přes vodu zprava doleva: kamera na jihu míří na sever (slunce vzadu), v pozadí vlek – voda je za kamerou; ověřit snímkem. **B**: kamera 3,6 m nad zemí (na žebříku/jeřábu), levá strana ve stínu. **C**: oprava QC: orbit 1,6 → 1,8 m, r = 5 → 4,2 m, cíl na truhlu s bateriemi (ly 0,2); keř u pickupu zůstává; orbit prochází zadní částí plošiny: stožár/anténa v záběru; ověřit snímkem. **D**: oprava QC: 7.7 kamera o 0,4 m doleva (je vidět truhla s bateriemi vlevo od dronu); voda v pozadí 7.6 – ověřit orientaci.

#### `middle-slozeni-odjezd`

- **Pokrývá:** middle-8.1, middle-8.2. **Místo a čas:** POLO → odjezd na východ, 12:30.
- **Akce:** t = 2 s `fold fold` (dron, žebřík, plachty, truhla, stožár; ≈ 10 s), potom `driveTo` (-555, 455) rychlostí 20 km/h, 9 s jízdy.
- **Izolace:** isolate keep=middle props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z7 roztočená vrtule u složeného vleku, trasa odjezdu (přímý bezstromový úsek).
- **Ověřit průzkumem:** odjezdová trasa na východ z POLO.
- **Soubory:** `scenes/middle-slozeni-odjezd.akce.json`, `middle-slozeni-odjezd.kamA.json`, `middle-slozeni-odjezd.kamB.json`, `middle-slozeni-odjezd.kamC.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | 8.1 odjezd kamery od vleku (ODJ) při skládání, 8.2 TRK L→R za odjíždějící soupravou | C | ODJ → TRK L→R · L→R | 36 / 30 | 2,8 → 3,4 m; 3,2 m | middle-8.1 2,0–12,0; middle-8.2 14,0–23,0 |
| B | 8.1 pevný vysoký záběr zezadu, 8.2 tele ze severu se sledováním cíle | C | STAT → STAT + sledování · R→L | 34 / 26 → 20 | 3,0 m; 3,2 m | middle-8.1 2,0–12,0; middle-8.2 14,0–23,0 |
| C | 8.1 oblet proti směru hodin, 8.2 FOL za soupravou | C / PC | ORB-CW → FOL · CW | 38 / 40 | 2,6 → 3,0 m, r = 10 m; 4,5 m | middle-8.1 2,0–12,0; middle-8.2 14,0–23,0 |

Rizika kamer: **A**: oprava QC: 8.1 odjezd kamery na sever (levý bok) a y ≥ 2,8 m místo rákosu na jihu; 8.2 z 18 m a výšky 3,2 m (keř u pickupu); trasa odjezdu na východ (z = 455) není ověřená; jih = voda; ověřit snímkem. **B**: oprava QC: 8.2 kamera ze stromu a keře (−666; 5; 445) na západ na osu odjezdu (−663; 3,2; 450), výhled podél trasy; 8.1 beze změny. **C**: oprava QC: oblet vede po levém boku (sever) bez rákosu, r = 10 m, y 2,6 → 3,0 m; 8.2 FOL vysoko a z boku (keř před trasou); FOL: kamera 14 m za vlekem při rozjezdu; ověřit snímkem.

### Blok 4: Potok u pole (POTOK): film max

#### `max-silnice`

- **Pokrývá:** max-1.1, max-2.1. **Místo a čas:** SIL (asfaltka z = −662,5, jízda na západ), 12:00.
- **Akce:** Souprava stojí na x = 90, yaw 270; tahač jede na západ do x = -95 rychlostí 36 km/h (mode line), záznam začíná 4,5 s po rozjezdu (souprava kolem x ≈ 60). MT655 s vlekem Max (dva drony na střeše, plachty svinuté, žebřík složen); silnice u potoka není souvislá, proto stejná SIL jako u ostatních.
- **Izolace:** isolate keep=max park=-690,150 props vehicles=true; ostatní soupravy parkují u farmy, mimo silnici.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** slunce: jih, kamery jen z jižní strany nebo zpoza kamery; sklon silnice 6,4° (groundCheck maxTilt 9); jízda nedeterministická (průjezd ±0,7 s, bočně ±0,3 m).
- **Ověřit průzkumem:** SIL: souvislá přímá silnice od x ≈ 95 do −95 (ověřeno jen +76…−80); kamery na jižní krajnici (z −649,5…−657,5): volné, bez keřů do 1 m od objektivu; azimut slunce v 12:00 a že A, D nemají slunce v objektivu.
- **Soubory:** `scenes/max-silnice.akce.json`, `max-silnice.kamA.json`, `max-silnice.kamB.json`, `max-silnice.kamC.json`, `max-silnice.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | tele ze západního konce silnice proti jízdě, souprava roste z dálky | C | STAT (pomalé oddálení) · – | 14 → 22 | 1,2 m nad krajnicí, z = −656 | max-1.1 0–8 |
| B | těsný průjezd z jižní strany, švenk po směru jízdy, konec ve 3/4 zezadu | PC→C | PAN-L (po směru jízdy) · R→L | 30 → 36 → 32 | 1,4 m, z = -649,5 (13 m od osy) | max-2.1 0,5–8,5 |
| C | ověřený záběr b02_road: pevná kamera 26 m od osy, švenk za tahačem | PC | PAN-L · R→L | 32 → 38 → 32 | 1,6 m, z = −636 (ověřeno) | max-2.1 0–7,5 |
| D | nízký tele pohled od konce silnice (druhá varianta 1.1), souprava projede těsně u kamery | C | STAT, tele, nízko · – | 12 | 0,8 m, z = −657,5, x = −80 | max-1.1 0–9 |

Rizika kamer: **A**: slunce vpravo (jih), jízdní stopa přímá; kamera ve stínu nesmí být; souprava se rozjíždí 4,5 s před záznamem (start x = 90). **B**: průjezd v čase ≈ 4 s (x kamery 20 = poloha soupravy 60 − 10 m/s · 4 s); odchylka ±0,7 s; keře na jižní straně ověřit. **C**: geometrie převzata z b02_road (ověřená), čas 10:00 místo 18:00 – slunce teď vzadu vpravo. **D**: kamera 5 m od osy: souprava proletí kolem v čase ≈ 14 s (mimo použitou část); Z4 – tráva v popředí do 1 m.

#### `max-zaparkovani`

- **Pokrývá:** max-3.2. **Místo a čas:** POTOK (674, -37), yaw 180, 12:10.
- **Akce:** Souprava jede po pásu k severu z bodu (674, -1) k cílovému bodu tahače (674, -43) (14 km/h) a zastaví; pravý bok (ventily) k potoku.
- **Izolace:** isolate keep=max props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** hráč, pumpa (nesmí být), keře u potoka.
- **Ověřit průzkumem:** POTOK: místo, vzdálenost tahač–kořen Maxu (odhad 12,6 m), rovina 30 × 25 m; orientace: potok na východě x ≈ 686 (z průzkumných snímků).
- **Soubory:** `scenes/max-zaparkovani.akce.json`, `max-zaparkovani.kamA.json`, `max-zaparkovani.kamB.json`, `max-zaparkovani.kamC.json`, `max-zaparkovani.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | nízko zezadu z pole: souprava dojede a zastaví zadním koncem k nám, potok vpravo v pozadí | PC | STAT nízko · – | 34 | 0,8 m, (666, -15) | max-3.2 1,0–13,0 |
| B | z potoka (východ) – levý bok k vodě? ne: pravý bok (ventily) k potoku, STAT | PC | STAT · – | 36 | 0,9 m, (685, -33) | max-3.2 1,0–13,0 |
| C | tele zdálky od jihu proti jízdě | C | STAT tele · – | 18 | 1,4 m, (670, 33) | max-3.2 1,0–13,0 |
| D | vyvýšený široký záběr ze západu (pole), v dálce farma a kopce | C | STAT · – | 40 | 3,5 m, (648, -35) | max-3.2 1,0–13,0 |

Rizika kamer: **A**: souprava jede od jihu kolem kamery (8 m): kamera mimo dráhu. **B**: kamera u vody: hladina a rákos v popředí, odlesk slunce. **C**: souprava přijíždí z míst, kde stojí kamera – start z = -1. **D**: kamera stojí v poli (plodina) – ověřit vlastnictví/škody.

#### `max-rozlozeni`

- **Pokrývá:** max-4.1. **Místo a čas:** POTOK, yaw 180 (pravý bok k potoku), 12:20.
- **Akce:** Max + MT655 složený; t = 2 s `fold unfold` (plachty, žebřík, stožár, oba drony; ≈ 9 s).
- **Izolace:** isolate keep=max props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z7 dron musí být složený při startu; úzký pás u potoka.
- **Ověřit průzkumem:** doba rozložení ≈ 9 s; oba drony se rozloží najednou.
- **Soubory:** `scenes/max-rozlozeni.akce.json`, `max-rozlozeni.kamA.json`, `max-rozlozeni.kamB.json`, `max-rozlozeni.kamC.json`, `max-rozlozeni.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | oblet po směru hodin od levého zadního rohu k levému boku (strana pole) | C | ORB-CW · CW | 40 → 38 | 2,0 → 3,4 m, r = 14 → 13 m | max-4.1 2,0–11,0 |
| B | oblet proti směru hodin od pravého zadního rohu k pravému boku (strana potoka, úzký pás) | C | ORB-CCW · CCW | 40 → 38 | 2,0 → 3,0 m, r = 9,5 → 8,5 m | max-4.1 2,0–11,0 |
| C | pevný záběr zezadu: dva drony se rozkládají na dvou plochách | C | STAT · – | 36 | 1,8 m, 14 m za vlekem | max-4.1 2,0–11,0 |
| D | boční jízda podél levého boku zepředu dozadu s jeřábem nahoru | PC | TRK + JIB-U · R→L | 38 | 1,2 → 3,4 m, 9 m od osy | max-4.1 2,0–11,0 |

Rizika kamer: **A**: kamera prochází polem (plodina). **B**: pás u potoka je úzký (≈ 11 m): orbit se přiblíží k vodě na x ≈ 684. **C**: oba drony musí být v záběru: vzdálenost 5,65 m, fov 36. **D**: pole vlevo: výška plodiny.

#### `max-detaily`

- **Pokrývá:** max-4.2, max-4.3, max-4.4, max-4.5, max-4.6. **Místo a čas:** POTOK, rozložený Max, 12:22.
- **Akce:** Stojící rozložený Max; okna 5,5 s od t = 2,0 / 7,5 / 13,0 / 18,5 / 24,0 s.
- **Izolace:** isolate keep=max props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z8 odlesk, stín tahače.
- **Ověřit průzkumem:** souřadnice cílů D1–D5 podle uzlů – kontrolní snímek; D3: víka kapes navíječů otevřená po rozložení.
- **Soubory:** `scenes/max-detaily.akce.json`, `max-detaily.kamA.json`, `max-detaily.kamB.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | TILT-U žebřík, TRK L→R plachty, NAJ truhla a navíječe, STAT dvě centrály, ODJ ventily a vápnová spojka | D | TILT-U / TRK L→R / NAJ / STAT / ODJ · různé | 30–40 | 0,5–3,5 m | max-4.2 2,0–7,5; max-4.3 7,5–13,0; max-4.4 13,0–18,5; max-4.5 18,5–24,0; max-4.6 24,0–29,5 |
| B | variace: NAJ žebřík zepředu, TRK R→L plachty, STAT truhla shora, NAJ centrály, NAJ vápnová spojka | D | NAJ / TRK R→L / STAT / NAJ / NAJ · opačné | 30–36 | 1,2–3,8 m | max-4.2 2,0–7,5; max-4.3 7,5–13,0; max-4.4 13,0–18,5; max-4.5 18,5–24,0; max-4.6 24,0–29,5 |

Rizika kamer: **A**: D5: kamera do x = −6,5 je 8,5 m od potoka; levá strana ve stínu; hadice na spojkách nesmí být. **B**: kamery u centrál 3–4 m od tahače: Z4 (kabina).

#### `max-pumpa`

- **Pokrývá:** max-5m.1, max-5m.2, max-5m.3, max-5m.4. **Místo a čas:** POTOK, pumpa mezi vlekem a potokem, 12:35.
- **Akce:** Pumpa (spawnMod + stationAt port 1, 3 m od ventilu nádrže A) stojí odpojená; t = 2,0 s `whPond` (sání do potoka), 3,5 s `whOut` (výstup na ventil A), 5,0 s `pumpOn`, běží do t = 14,0 s, potom `pumpOff` + `removeVehicle waterPump` (hadice zmizí s pumpou), 5m.4 = stejný rám bez pumpy. Hlavní nádrž prázdná.
- **Izolace:** isolate keep=max props vehicles (před spawnem pumpy); mlýnek, big bag, násypka nesmí existovat.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z2 jen pumpa a hadice; sací koš ≥ 0,15 m pod hladinou do 8 m od pumpy; odlesk na hladině; stejné světlo 5m.3/5m.4 (setTime lock).
- **Ověřit průzkumem:** whPond najde vodu ≥ 0,15 m do 8 m od vstupní spojky pumpy (pumpa ≈ (677.2, -30.0), potok x ≈ 686); pumpa stojí na straně ventilu (pravý bok = −x v souřadnicích Maxu, ne levý jako píše scénář); po removeVehicle ventil volný a žádná hadice nevisí.
- **Soubory:** `scenes/max-pumpa.akce.json`, `max-pumpa.kamA.json`, `max-pumpa.kamB.json`, `max-pumpa.kamC.json`, `max-pumpa.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | 5m.1 TRK R→L podél břehu: pumpa, hadice, motor naskočí a hadice se napnou | C | TRK R→L · R→L | 38 | 1,4 m, x = −7,5 (potok za kamerou) | max-5m.1 0,5–7,0; max-5m.3 11,0–13,5; max-5m.4 14,2–15,7 |
| B | 5m.1 pevná širší kamera, 5m.2 jeřáb dolů k hladině se sacím košem pod vodou (VSTUP modrá, VÝSTUP červená) | C / D | STAT → JIB-D · – | 36 → 40 → 34 | 1,7 m; 3,8 → 1,1 m | max-5m.1 0,5–7,0; max-5m.2 7,5–10,5; max-5m.3 11,0–13,5 |
| C | uzamčený rám: pumpa běží (5m.3), po 14,0 s tentýž rám bez pumpy (5m.4, střih na shodu) | D | STAT (uzamčený) · – | 38 | 1,0 m, x = −8,8 | max-5m.1 0,5–7,0; max-5m.3 11,0–13,5; max-5m.4 14,2–15,7 |
| D | 5m.2 druhý jeřáb z druhé strany a druhý uzamčený rám pro 5m.3/5m.4 | C / D | JIB-D → STAT (uzamčený) · – | 40 → 34 / 34 | 3,2 → 1,0 m; 1,2 m | max-5m.1 0,5–7,0; max-5m.2 7,5–10,5; max-5m.3 11,0–13,5; max-5m.4 14,2–15,7 |

Rizika kamer: **A**: pumpa a ventil v záběru, kamera na straně pole (W), tráva a rákos za pumpou. **B**: odlesk slunce na hladině přes štítky (Z8); poloha sacího koše (konec 10 m hadice) neznámá – cíl (−9,5; 0; −1,5) odhad. **C**: kamera se nesmí hýbat ani zoomovat; hladina a tráva se hýbou i v „stejném“ rámu. **D**: stejné riziko jako B; kamera na poli.

#### `max-mlynek`

- **Pokrývá:** max-5m.5, max-5m.6, max-5m.7, max-5m.8. **Místo a čas:** POTOK, mlýnek za pravým bokem Maxu, 12:42.
- **Akce:** Mlýnek stojí samostatně (yaw 0, kořen (677.8, -26.0), výstup ≈ 7 m od vápnové spojky Maxu, nezapřažen). t = 2 s `dbg whConnect5` (hadice mlýnek → vápnová spojka), 7,5 s `bagLift target=mill` (big bag LIME 300 l), 17 s `millOn` (motor, zelený prstenec), 21 s `whValve` (kohout), 29 s `millOff`.
- **Izolace:** isolate keep=max props vehicles (před spawnem mlýnku); pumpa nesmí existovat.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z2 jen mlýnek a big bag, Z9, prach ani tok vápna nejsou vidět, mlýnek ≤ 8 m od spojky (hadice 12 m), úzký pás u potoka.
- **Ověřit průzkumem:** číslo vápnové spojky pro `dbg whConnect<N>` (5 z c63c) – `dbg whStatus`; bagLift target=mill vyklopí big bag do mlýnku (N6); poloha mlýnku (677.8, -26.0) stojí na souši, ≤ 8 m od spojky; prstenec `millStartRing` svítí při millOn.
- **Soubory:** `scenes/max-mlynek.akce.json`, `max-mlynek.kamA.json`, `max-mlynek.kamB.json`, `max-mlynek.kamC.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | 5m.5 oblet proti směru hodin kolem hadice, 5m.6 sledování klesajícího big bagu, 5m.7 nájezd na mlýnek, 5m.8 TRK L→R | C / PC / D | ORB-CCW → TILT-D → NAJ → TRK L→R · L→R (5m.8) | 40 / 40 / 34 / 38 | 1,8 → 1,5 m; 1,6 m; 1,4 m; 1,7 m | max-5m.5 0,5–7,5; max-5m.6 8,0–16,5; max-5m.7 17,0–20,5; max-5m.8 21,0–29,0 |
| B | 5m.5 pevně z odstupu, 5m.6 pohled shora z boku, 5m.7 detail z konce, 5m.8 oblet po směru hodin kolem hadice | C / PC / D | STAT → STAT → NAJ → ORB-CW · CW (5m.8) | 36 / 38 / 32 / 40 | 2,0 m; 2,2 m; 1,3 m; 1,8 m | max-5m.5 0,5–7,5; max-5m.6 8,0–16,5; max-5m.7 17,0–20,5; max-5m.8 21,0–29,0 |
| C | 5m.5 tele zdálky na spojku, 5m.6 vyvýšený záběr na vyklopení, 5m.7 šnek a motor z boku, 5m.8 FOL-like boční jízda | C / PC / D | STAT tele → STAT → NAJ → TRK R→L · R→L (5m.8) | 24 / 36 / 32 / 38 | 1,5 m; 3,5 m; 1,2 m; 1,7 m | max-5m.5 0,5–7,5; max-5m.6 8,0–16,5; max-5m.7 17,0–20,5; max-5m.8 21,0–29,0 |

Rizika kamer: **A**: 5m.6: bagLift s big bagem LIME nad exactFillRootNode mlýnku je neověřený (záloha: násypka c62); big bag se objeví až po ≈ 0,5 s (kamera ho dostihne v t = 8,0 s); Z9 spodek big bagu ≥ 1,5 m. **B**: kamera 5m.8 na východní straně 6,5 m od středu hadice: x ≈ 684.3 (potok 686). **C**: kamera u mlýnku: mlýnek ≈ 2,3 m od Maxu, mezera úzká.

#### `max-planovac`

- **Pokrývá:** max-6.1, max-6.2, max-6.3, max-6.4. **Místo a čas:** POTOK, plánovač, 13:05.
- **Akce:** t = 1 s `screenWake`, 6 s plánovač; 7 s vybráno blízké pole 59 (u potoka), 9,9 s skok výběru na vzdálenější pole 60 (strniště); 14,9 s karta (stránka 2), 19,4 s mapa; 19,9 / 22,4 / 24,9 s `flightArea` pole 60: 3, 4, 5 bodů (fialová plocha od Maxu k poli).
- **Izolace:** isolate keep=max park=260,-665 (ikony cizích vleků mimo okno mapy), relayRemove.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z5 kurzor, hlášky, světové čáry; plocha po bodech (O4); pole 60 v dosahu 153 m ✓; ikony cizích vozidel.
- **Ověřit průzkumem:** ID polí u POTOKU: blízké 59 (brambory, střed (635, 25)), vzdálené 60 (535, 33); pole 60 jako strniště (`setField growth=cut`); body plochy (HOME ≈ (674, -29)) – plocha po každém bodu hned vidět; plannerPage 2 = karta s pruhem výšky přeletu; planner nekreslí přelety ani překážky (jen fialová plocha).
- **Soubory:** `scenes/max-planovac.akce.json`, `max-planovac.kamA.json`, `max-planovac.kamB.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | displej na vleku (STAT), mapa: skok výběru na vzdálenější pole a přiblížení (MAPA+), karta, fialová plocha + pomalý posun mapy doprava (MAPA-R) | D / UI | STAT → MAPA+ → STAT → MAPA-R · R (posun mapy) | 32 (svět) | 1,8 m, 3,8 m od displeje | max-6.1 0,5–5,5; max-6.2 7,5–14,9; max-6.3 15,2–19,4; max-6.4 20,0–28,9 |
| B | nájezd na displej, mapa: oddálená úvodní scéna, zoom na vzdálené pole, plocha (MAPA-R) | D / UI | NAJ → MAPA+ → MAPA-R · R (posun mapy) | 32 → 28 (svět) | 1,5 m | max-6.1 0,5–5,5; max-6.2 7,5–14,9; max-6.3 15,2–19,4; max-6.4 20,0–28,9 |

Rizika kamer: **A**: karta pole: pruh „Výška přeletu 20 m“ (jen je-li pole za překážkami); Z5: červená hláška „Vlek stojí mimo letovou plochu“ nesmí být; světové čáry (Alt+5) vypnuty. **B**: plocha musí být vidět po každém bodu (O4): planner ji překreslí hned? záloha: jen hotová plocha.

#### `max-let`

- **Pokrývá:** max-7.0, max-7.1, max-7.2, max-7.3, max-7.4. **Místo a čas:** POTOK → pole 60 (535, 33) – strniště, 13:15.
- **Akce:** t = 2 s dron 1 na plošině (7.0), t = 6,5 s `startFlight drone=0` (druhý dron o ≈ 3 s později), `coverLines auto2` (jen dvě sousední dráhy), `waitDrone spraying` oba, značky w1b/w2/w3 po 6,5 s (7.2–7.4), `returnHome` obou.
- **Izolace:** isolate keep=max props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z7 dron v zeleni, formace dvou dronů (O6), vítr, let 153 m, koruny nad plošinami; TOP statický zachytí dráhy až po kalibraci.
- **Ověřit průzkumem:** coverLines: sousední dráhy dvou dronů (čísla řádků od okraje pole, auto2); dron 2 startuje s odstupem ≈ 3 s; pole 60 jako strniště a v dosahu dronů (153 m).
- **Soubory:** `scenes/max-let.akce.json`, `max-let.kamA.json`, `max-let.kamB.json`, `max-let.kamC.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | 7.0 NAJ na dron 1, 7.1 jeřáb nahoru za oběma drony, 7.2 FOL obou (kamera vlevo od osy), 7.3 TOP nad oběma, 7.4 boční tracking zleva | D / C / PC | NAJ → JIB-U → FOL → TOP → TRK · R→L (7.4) | 32 → 28 / 38 / 38 / 44 / 32 | 0,5–0,9 m; 1,4 → 6,5 m; 3 m; 32 m; 1,5 m | max-7.0 t=2,0–t=5,0; max-7.1 start +0–start +7; max-7.2 w1b +0–w1b +6,5; max-7.3 w2 +0–w2 +6,5; max-7.4 w3 +0–w3 +6,5 |
| B | 7.0 NAJ na dron 2, 7.1 pevná kamera zepředu vpravo (naklání se), 7.2 FOL vysoko, 7.3 TOP statický nad vzdáleným polem, 7.4 tracking zprava | D / C / PC | NAJ → STAT → FOL → TOP statický → TRK · L→R (7.4) | 30 / 40 / 38 / 48 / 32 | 0,5–0,9 m; 1,3 m; 8 m; 110 m; 1,5 m | max-7.0 t=2,0–t=5,0; max-7.1 start +0–start +7; max-7.2 w1b +0–w1b +6,5; max-7.3 w2 +0–w2 +6,5; max-7.4 w3 +0–w3 +6,5 |
| C | 7.0 zepředu, 7.1 jeřáb zleva zezadu, 7.2 FOL zepředu 3/4, 7.3 TOP vysoko, 7.4 FOL nízko zezadu | D / C / PC | NAJ → JIB-U → FOL (čelo) → TOP → FOL nízko · – | 28 / 36 / 38 / 30 / 36 | 0,4–0,7 m; 1,0 → 6 m; 2 m; 48 m; 1,2 m | max-7.0 t=2,0–t=5,0; max-7.1 start +0–start +7; max-7.2 w1b +0–w1b +6,5; max-7.3 w2 +0–w2 +6,5; max-7.4 w3 +0–w3 +6,5 |

Rizika kamer: **A**: druhý dron startuje ≈ 3 s po prvním (plošina); coverLines: oba drony stříkají sousední dráhy (O6); 7.1: koruny, pojistka dronu. **B**: TOP statický: kamera 110 m nad středem pole 60; dráhy dronů podle coverLines – nutný kalibrační běh. **C**: FOL zepředu: držet ≥ 10 m před drony; TOP 48 m nad dronem při fov 30 zachytí jen jeden dron.

#### `max-navrat-servis`

- **Pokrývá:** max-7.5, max-7.6, max-7.7. **Místo a čas:** POTOK, 13:30.
- **Akce:** Hlava: `startFlight drone=0`, po vzletu obou +2,5 s `droneSet battery 0,2 tank 1,5` pro oba (vrací se), čeká na `near 40 m` dronu 1; záznam začíná při příletu; `waitDrone servicing drone 1`, značka, servis 14 s; dron 2 čeká.
- **Izolace:** isolate keep=max props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** přistání po sobě (nedeterministické), kamera 3 m od drony.
- **Ověřit průzkumem:** dron 2 přistává po drony 1 (přední plocha první) a nezačne servis dřív než dron 1.
- **Soubory:** `scenes/max-navrat-servis.akce.json`, `max-navrat-servis.kamA.json`, `max-navrat-servis.kamB.json`, `max-navrat-servis.kamC.json`, `max-navrat-servis.kamD.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | 7.5 tele pevně: oba drony se vracejí a po sobě přistávají, 7.6 oblet proti směru hodin kolem dronu 1 na desce | PC | STAT tele → ORB-CCW · CCW | 24 / 40 | 1,4 m; orbit 2,4 → 2,0 m, r = 7 → 5,5 | max-7.5 0,0–7,0; max-7.6 servicing +0–servicing +12 |
| B | 7.5 nízká statika zleva zezadu, 7.7 detail výměny baterie v truhle (kamera nad palubou) | PC / D | STAT → NAJ · – | 34 / 36 → 30 | 1,0 m; 3,6 m | max-7.5 0,0–7,0; max-7.7 servicing +0–servicing +10 |
| C | 7.5 FOL za sestupem dronu 1, 7.6 oblet po směru hodin | PC | FOL → ORB-CW · CW | 34 / 38 | 2,4 m; orbit 2,0 → 2,2 m | max-7.5 0,0–7,0; max-7.6 servicing +0–servicing +12 |
| D | 7.5 shora zprava, 7.7 detail dronu a hadice zblízka | PC / D | STAT → ODJ · – | 34 / 28 | 3,0 m; 0,6 m | max-7.5 0,0–7,0; max-7.7 servicing +0–servicing +10 |

Rizika kamer: **A**: druhý dron přistává ≈ 3 s po prvním; v 7.6 se druhý dron může objevit v záběru (čeká). **B**: truhla (0,96; 2,79; −2,47) je 2,6 m od dronu 1 (z = 0,1) – oba v záběru z levého boku. **C**: FOL se zastaví po přistání; dron 2 se může objevit. **D**: kamera 5 m nad zemí vpravo vpředu (jeřáb); tele z paluby.

#### `max-slozeni-odjezd`

- **Pokrývá:** max-8.1, max-8.2. **Místo a čas:** POTOK → odjezd k severu, 13:45.
- **Akce:** t = 2 s `fold fold` (drony, kapsy navíječů, žebřík, plachty; ≈ 9 s), potom `driveTo` (675, -78) 18 km/h, 10 s jízdy k silnici.
- **Izolace:** isolate keep=max props vehicles.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z7 roztočené vrtule, mlýnek a pumpa nesmí být, trasa k silnici (z = -84).
- **Ověřit průzkumem:** trasa z pásu k silnici na sever (přejezd příkopu).
- **Soubory:** `scenes/max-slozeni-odjezd.akce.json`, `max-slozeni-odjezd.kamA.json`, `max-slozeni-odjezd.kamB.json`, `max-slozeni-odjezd.kamC.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | 8.1 jeřáb dolů při skládání, 8.2 pevný tele zezadu za odjíždějící soupravou | C | JIB-D → STAT tele · – | 38 / 16 | 6,0 → 1,6 m; 1,4 m | max-8.1 2,0–11,0; max-8.2 13,0–23,0 |
| B | 8.1 oblet proti směru hodin, 8.2 tele z východu přes potok se sledováním cíle | C | ORB-CCW → STAT + sledování · CCW / R→L | 40 / 22 | 2,0 → 3,0 m; 1,3 m | max-8.1 2,0–11,0; max-8.2 13,0–23,0 |
| C | 8.1 pevný nízký záběr zezadu, 8.2 FOL za soupravou | C / PC | STAT → FOL · – | 36 / 40 | 1,4 m; 3,0 m | max-8.1 2,0–11,0; max-8.2 13,0–23,0 |

Rizika kamer: **A**: 8.2: souprava jede k severu po pásu a silnici – výhled mezi kamerou a pásem. **B**: kamera 14 m východně: u potoka; orbit r = 12 m je na východě už ve vodě – zkrátit. **C**: FOL: 18 m za tahačem při rozjezdu.

### Blok 5: Dvůr farmy: epilog a produktová scéna

#### `spol`

- **Pokrývá:** spol-1, spol-2, spol-3. **Místo a čas:** DVŮR (−694, 138), tři vleky (c02_three_wide), 13:00.
- **Akce:** Mini + JD 3650 (−705, 138), Max + MT655 (−694, 136), Middle + pickup (−683, 138), yaw 180, rozložené; čtyři drony (Mini 1, Max 2, Middle 1) vzlétnou a `droneHover` je drží 34 s nad vleky.
- **Izolace:** rekvizity smazány (`removeVehicle`), žádná pumpa, mlýnek ani big bag; všechny tři vleky jsou ve scéně (jediná výjimka ze Z1).
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** drony odletí z obrazu po vypršení hoveru, 4 drony najednou (výkon), překrývání vleků; Z7 dron mimo záběr.
- **Ověřit průzkumem:** `droneHover` drží drony nad vleky po vzletu (výška, doba); výkon hry se 4 drony (≥ 55 fps); zachování mezer mezi vleky.
- **Soubory:** `scenes/spol.akce.json`, `spol.kamA.json`, `spol.kamB.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | spol-1 pomalé najetí zdálky na tři vleky se startujícími drony, spol-2 boční jízda zezadu L→R, spol-3 jeřáb nahoru | C / PC | NAJ → TRK L→R → JIB-U · L→R | 44 / 50 / 50 | 1,6 → 2,2 m; 1,7 m; 1,6 → 14 m | spol-1 t=0–h1 +4; spol-2 h2 +0–h2 +8; spol-3 h3 +0–h3 +8 |
| B | spol-1 pevný široký záběr ze západu, spol-2 jízda zepředu R→L, spol-3 oblet nad řadou | C / PC | STAT → TRK R→L → ORB-CW · R→L / CW | 42 / 46 / 50 | 2,0 m; 1,7 m; 3 → 16 m | spol-1 t=0–h1 +4; spol-2 h2 +0–h2 +8; spol-3 h3 +0–h3 +8 |

Rizika kamer: **A**: drony letí za ~34 s od vzletu; droneHover po `airborne` + 2 s – výška visení ověřit; mezera mezi vleky ≥ 4 m (c02: 11–12 m od osy k ose). **B**: kamera na severu (z = 112): pole 1 (parcela), volný výhled? stín vleků; oblet 26 m překračuje stodolu na jihu (z ≈ 190) ne.

#### `prod-rada`

- **Pokrývá:** prod-2, prod-3, prod-4, prod-5, prod-8. **Místo a čas:** BET (náhrada: dvůr, -712, 152), 13:00.
- **Akce:** Řada zleva doprava na rovné ploše (z = 152): kanystr hnojiva, herbicidu, nafty, pytel vápna, big bag, pumpa, násypka, reléová tyč (mezery ≥ 0,5 m; x = -712.0, -711.0, -710.0, -708.6, -706.7, -704.4, -701.8, -698.4). Vleky mimo záběr (Mini zaparkován na (300, −665)).
- **Izolace:** isolate keep=mini (Mini odvezen mimo scénu), props smazány před spawnem.
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z2 cizí předměty, Z8 odlesk, štítky otočeny ke kameře? (yaw 180), pytel/big bag/kanystry kinematické (still).
- **Ověřit průzkumem:** BET: rovný beton (průzkum určí; náhrada = dvůr); yaw předmětů: štítky směrem k +z; spawnCanister kind=limebag, spawnMod big bag s fill SDT_FINE_LIME; relé tyč rozložená a zelený LED po `relaySpawn`.
- **Soubory:** `scenes/prod-rada.akce.json`, `prod-rada.kamA.json`, `prod-rada.kamB.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | prod-2 TRK L→R se zastaveními 2,4 s u kanystrů a pytle, prod-3 TILT-U big bag, prod-4 TRK R→L násypka a pumpa, prod-5 ORB-CW reléová tyč, prod-8 ODJ celek | D / C | TRK / TILT-U / TRK / ORB / ODJ · L→R, R→L, CW | 30 / 30 / 32 / 35 / 45 | 0,45–2,0 m | prod-2 2,0–15,2; prod-3 15,7–21,2; prod-4 22,2–31,2; prod-5 31,7–39,2; prod-8 39,7–45,2 |
| B | prod-2 TRK R→L (opačné pořadí), prod-3 NAJ na big bag, prod-4 TRK L→R pumpa pak násypka, prod-5 ORB-CCW tyč, prod-8 pevný vyvýšený celek | D / C | TRK / NAJ / TRK / ORB / STAT · R→L, L→R, CCW | 30 / 30 / 32 / 35 / 40 | 0,8–3,0 m | prod-2 2,0–15,2; prod-3 15,7–21,2; prod-4 22,2–31,2; prod-5 31,7–39,2; prod-8 39,7–45,2 |

Rizika kamer: **A**: čitelnost štítků z fov 30 ověřit; směr štítků (yaw 180) ověřit; Z8 odlesk na štítku, stín kamery na předmětu. **B**: reléová tyč (rozložená, zelený LED) – orbit r 3,4 m: kamera nesmí vjet do tyče.

#### `prod-vleky`

- **Pokrývá:** prod-1, prod-6, prod-7. **Místo a čas:** BET (náhrada: dvůr), vleky v pozadí, 13:00.
- **Akce:** Řada předmětů jako v `prod-rada` (z = 152); za ní tři rozložené vleky (tahače na z = 118, yaw 180, x = −708 / −694 / −680) s drony S (Mini), M (Middle), L (Max, `padDrone`), centrály s nabitými bateriemi.
- **Izolace:** rekvizity smazány a znovu naspawnovány; všechny tři vleky jsou ve scéně (výjimka Z1 pro prod-1, 6, 7).
- **Střih (in/out):** užitečné okno každého záběru je v tabulce kamer (sekundy od značky; klip začíná o 0,5 s dřív). Rezerva 2 s před a po akci je ve všech kamerách.
- **Rizika:** Z1 jen v těchto záběrech; drony M a L (padDrone) – ověřit; vleky stojí 30 m za řadou (rozmazání pozadí není).
- **Ověřit průzkumem:** `padDrone` M pro Middle a L pro Max; tahače na z = 118 mají volné místo (pole 1 na severu); baterie viditelné v truhle Mini.
- **Soubory:** `scenes/prod-vleky.akce.json`, `prod-vleky.kamA.json`, `prod-vleky.kamB.json`.

| kam | popis | typ | pohyb · směr | fov | výška / odstup | záběry (od–do, s) |
|---|---|---|---|---|---|---|
| A | prod-1 NAJ na celou řadu s vleky v pozadí, prod-6 NAJ na baterie v otevřené truhle Mini, prod-7 TRK L→R podél tří vleků s drony S, M, L | C / D / PC | NAJ → NAJ → TRK L→R · L→R | 42 / 28 / 38 | 1,8 → 2,2 m; 1,5 m; 1,8 m | prod-1 0,0–6,5; prod-6 7,0–12,0; prod-7 12,5–21,5 |
| B | prod-1 pevný celek z odstupu, prod-6 NAJ na truhlu Middle (vzpěry), prod-7 TRK R→L | C / D / PC | STAT → NAJ → TRK R→L · R→L | 40 / 32 / 38 | 1,8 m; 3,6 m; 1,8 m | prod-1 0,0–6,5; prod-6 7,0–12,0; prod-7 12,5–21,5 |

Rizika kamer: **A**: prod-6: truhla Mini otevřená po rozložení?; baterie viditelné; prod-7: M a L drony (padDrone) – nejisté; Z1 výjimka platí jen pro prod-1, 6, 7. **B**: kamera 3,6 m nad zemí (jeřáb), truhla Middle vlevo-vpředu.

## 7. Pokrytí záběrů kamerami

| záběr | kamery |
|---|---|
| mini-1.1 | mini-silnice/A, mini-silnice/D |
| mini-2.1 | mini-silnice/B, mini-silnice/C |
| mini-3.1 | mini-cesta/A, mini-cesta/B, mini-cesta/C, mini-cesta/D |
| mini-3.2 | mini-dvur-prijezd/A, mini-dvur-prijezd/B, mini-dvur-prijezd/C, mini-dvur-prijezd/D |
| mini-4.1 | mini-rozlozeni/A, mini-rozlozeni/B, mini-rozlozeni/C, mini-rozlozeni/D |
| mini-4.2 | mini-detaily/A, mini-detaily/B |
| mini-4.3 | mini-detaily/A, mini-detaily/B |
| mini-4.4 | mini-detaily/A, mini-detaily/B |
| mini-4.5 | mini-detaily/A, mini-detaily/B |
| mini-4.6 | mini-detaily/A, mini-detaily/B |
| mini-5.1 | mini-kanystr/A, mini-kanystr/B, mini-kanystr/D |
| mini-5.2 | mini-kanystr/A, mini-kanystr/B, mini-kanystr/C, mini-kanystr/D |
| mini-6.1 | mini-planovac/A, mini-planovac/B |
| mini-6.2 | mini-planovac/A, mini-planovac/B |
| mini-6.3 | mini-planovac/A, mini-planovac/B |
| mini-7.1 | mini-let/A, mini-let/B, mini-let/C |
| mini-7.2 | mini-let/A, mini-let/B, mini-let/C |
| mini-7.3 | mini-let/A, mini-let/B, mini-let/C |
| mini-7.4 | mini-let/A, mini-let/B, mini-let/C |
| mini-7.5 | mini-navrat-servis/A, mini-navrat-servis/B, mini-navrat-servis/C, mini-navrat-servis/D |
| mini-7.6 | mini-navrat-servis/A, mini-navrat-servis/C |
| mini-7.7 | mini-navrat-servis/B, mini-navrat-servis/D |
| mini-8.1 | mini-slozeni-odjezd/A, mini-slozeni-odjezd/B, mini-slozeni-odjezd/C |
| mini-8.2 | mini-slozeni-odjezd/A, mini-slozeni-odjezd/B, mini-slozeni-odjezd/C |
| middle-1.1 | middle-silnice/A, middle-silnice/D |
| middle-2.1 | middle-silnice/B, middle-silnice/C |
| middle-3.1 | middle-cesta/A, middle-cesta/B, middle-cesta/C, middle-cesta/D |
| middle-3.2 | middle-polo-prijezd/A, middle-polo-prijezd/B, middle-polo-prijezd/C, middle-polo-prijezd/D |
| middle-4.1 | middle-rozlozeni/A, middle-rozlozeni/B, middle-rozlozeni/C, middle-rozlozeni/D |
| middle-4.2 | middle-detaily/A, middle-detaily/B |
| middle-4.3 | middle-detaily/A, middle-detaily/B |
| middle-4.4 | middle-detaily/A, middle-detaily/B |
| middle-4.5 | middle-detaily/A, middle-detaily/B |
| middle-4.6 | middle-detaily/A, middle-detaily/B |
| middle-5.1 | middle-kanystr/A, middle-kanystr/B, middle-kanystr/C |
| middle-5.2 | middle-kanystr/A, middle-kanystr/B, middle-kanystr/C |
| middle-6.1 | middle-planovac/A, middle-planovac/B |
| middle-6.2 | middle-planovac/A, middle-planovac/B |
| middle-6.3 | middle-planovac/A, middle-planovac/B |
| middle-7.0 | middle-let/A, middle-let/B, middle-let/C |
| middle-7.1 | middle-let/A, middle-let/B, middle-let/C |
| middle-7.2 | middle-let/A, middle-let/B, middle-let/C |
| middle-7.3 | middle-let/A, middle-let/B, middle-let/C |
| middle-7.4 | middle-let/A, middle-let/B, middle-let/C |
| middle-7.5 | middle-navrat-servis/A, middle-navrat-servis/B, middle-navrat-servis/C, middle-navrat-servis/D |
| middle-7.6 | middle-navrat-servis/A, middle-navrat-servis/C |
| middle-7.7 | middle-navrat-servis/B, middle-navrat-servis/D |
| middle-8.1 | middle-slozeni-odjezd/A, middle-slozeni-odjezd/B, middle-slozeni-odjezd/C |
| middle-8.2 | middle-slozeni-odjezd/A, middle-slozeni-odjezd/B, middle-slozeni-odjezd/C |
| max-1.1 | max-silnice/A, max-silnice/D |
| max-2.1 | max-silnice/B, max-silnice/C |
| max-3.1 |  |
| max-3.2 | max-zaparkovani/A, max-zaparkovani/B, max-zaparkovani/C, max-zaparkovani/D |
| max-4.1 | max-rozlozeni/A, max-rozlozeni/B, max-rozlozeni/C, max-rozlozeni/D |
| max-4.2 | max-detaily/A, max-detaily/B |
| max-4.3 | max-detaily/A, max-detaily/B |
| max-4.4 | max-detaily/A, max-detaily/B |
| max-4.5 | max-detaily/A, max-detaily/B |
| max-4.6 | max-detaily/A, max-detaily/B |
| max-5m.1 | max-pumpa/A, max-pumpa/B, max-pumpa/C, max-pumpa/D |
| max-5m.2 | max-pumpa/B, max-pumpa/D |
| max-5m.3 | max-pumpa/A, max-pumpa/B, max-pumpa/C, max-pumpa/D |
| max-5m.4 | max-pumpa/A, max-pumpa/C, max-pumpa/D |
| max-5m.5 | max-mlynek/A, max-mlynek/B, max-mlynek/C |
| max-5m.6 | max-mlynek/A, max-mlynek/B, max-mlynek/C |
| max-5m.7 | max-mlynek/A, max-mlynek/B, max-mlynek/C |
| max-5m.8 | max-mlynek/A, max-mlynek/B, max-mlynek/C |
| max-6.1 | max-planovac/A, max-planovac/B |
| max-6.2 | max-planovac/A, max-planovac/B |
| max-6.3 | max-planovac/A, max-planovac/B |
| max-6.4 | max-planovac/A, max-planovac/B |
| max-7.0 | max-let/A, max-let/B, max-let/C |
| max-7.1 | max-let/A, max-let/B, max-let/C |
| max-7.2 | max-let/A, max-let/B, max-let/C |
| max-7.3 | max-let/A, max-let/B, max-let/C |
| max-7.4 | max-let/A, max-let/B, max-let/C |
| max-7.5 | max-navrat-servis/A, max-navrat-servis/B, max-navrat-servis/C, max-navrat-servis/D |
| max-7.6 | max-navrat-servis/A, max-navrat-servis/C |
| max-7.7 | max-navrat-servis/B, max-navrat-servis/D |
| max-8.1 | max-slozeni-odjezd/A, max-slozeni-odjezd/B, max-slozeni-odjezd/C |
| max-8.2 | max-slozeni-odjezd/A, max-slozeni-odjezd/B, max-slozeni-odjezd/C |
| spol-1 | spol/A, spol/B |
| spol-2 | spol/A, spol/B |
| spol-3 | spol/A, spol/B |
| prod-1 | prod-vleky/A, prod-vleky/B |
| prod-2 | prod-rada/A, prod-rada/B |
| prod-3 | prod-rada/A, prod-rada/B |
| prod-4 | prod-rada/A, prod-rada/B |
| prod-5 | prod-rada/A, prod-rada/B |
| prod-6 | prod-vleky/A, prod-vleky/B |
| prod-7 | prod-vleky/A, prod-vleky/B |
| prod-8 | prod-rada/A, prod-rada/B |

## 8. Kontrola a úklid

- `python tools/cinema/v2/mk_take.py --dry` projde všechny akce × kamery; `python tools/cinema/v2/mk_take.py <akce> <kam>` zapíše `tools/cinema/scenes/v2_<akce>_<kam>.json`.
- **Úklid po natáčení (F5):** `selectField own=true` trvale mění vlastnictví polí 4, 59, 60, 91; `flightArea field=all mode=clear`, `ui close`, `ui relayRemove`, odstranit rekvizity (pumpa, mlýnek, big bag, násypka), `isolate undo` (vozidla), `camStop`. Hru neukládat.
- Před akcí s dronem `play command=windOff`; první take každé jízdy zalogovat `tel=true` (`tel_analyze.py`), u letů `trace on`; `clips.json` doplnit `t_event`, `sync_dev` (prompt 04/05).
