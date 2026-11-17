# Návrh: plnění big bagu z mlýnku výsypnou rourou + výsypná stolice na mobilní násypce

Stav 2026-10-29: **jen návrh**, v modu se nic nezměnilo. Koncept je v samostatných souborech
`out/mill_concept/concept_mill.blend` a `concept_hopper.blend`, postavených skriptem `out/mill_concept/concept.py`
(`blender -b --factory-startup --python out/mill_concept/concept.py -- mill|hopper`). Skript mod jen čte přes importer i3d
z `out/check_body`. Souřadnice v celém dokumentu jsou **i3d**: X vlevo (−X = pravý bok), Y nahoru, Z dopředu, země y = 0.
Oranžové díly na renderech jsou nové.

## 0. Výchozí fakta (změřeno)

| co | hodnota | odkud |
|---|---|---|
| vanilla big bag (`$data/objects/bigBag/bigBag.i3d`) | kořen u dna; tělo 0,99 (x) × 0,84 (z); horní plocha látky 1,10–1,18 m; **jedno poutko uprostřed nahoře** (oblouk v rovině x–y, nohy na x ±0,16) do 1,73 m (kolize háku do 1,81 m) | sonda `probe.py`, paprsky na `bigBag_vis` |
| `dischargeActivationTrigger` vaku | kvádr 0,63 × 3,8 × 0,56 **pod dnem** vaku (y −3,73…0,07), vypouštění při plnicím objektu pod vakem | `bigBag.i3d`, `bigBag.xml` (`dischargeNode … activationTrigger`, `canStartDischargeAutomatically`) |
| mlýnek | obrys x ±1,255, záď (světla/nárazník) z −2,53, rám z −2,31; nádobka jemného vápna x −1,00…−0,38, z −0,08…0,40; spojka `millOutletPort` (−1,00; 0,70; 0,15); blatník x −0,92…−1,25, z −0,94…−1,82; pravé nohy násypky x −0,79, z −0,72 a −2,14; lem paluby x −0,88…−0,92 do y 0,66 | `probe.py`, `probe_legs.py` |
| násypka hrubého vápna mlýnku | výsyp y 1,00, šikmé stěny do 1,72 × 1,56 na y 2,05, svislý lem do 2,40; vnitřek do 2,40 ≈ **2 090 l** (fill unit 2 400 l = s kupkou) | výpočet v `concept.py` |
| mobilní násypka | lievec 0,18 → 0,80 m, dno y 0,47, ústí y 1,02 → **≈150 l** geometricky, ale fill unit má 500 l | `blender/build_hopper.py`, `objects/hopper/limeHopper.xml` |
| klávesy | `TOGGLE_PIPE` = **O**, `IMPLEMENT_EXTRA3` = **Y** | `profileTemplate/inputBindingDefault_KeyboardMouse.xml:240, 268` |

Dnešní foukací roura (`blowPipe.i3d`) končí ústím na y 2,00, 1,55 m od spojky – to je ta „zbytečně vysoko“.

## 1. Rozložení na mlýnku

**Potrubí po palubě (DN 100, Ø 0,10):** z nového rozdělovače pod nádobkou jemného vápna (−0,80; 0,70; 0,15) dozadu,
uhne dovnitř na x −0,67 (mezi lem paluby a nohy násypky, osa y 0,68, tři objímky na palubě), pod násypkou až na
z −2,26 (za zadní pravou nohou násypky), tam ven přes lem paluby do **stoupačky v pravém zadním rohu** (−1,03; z −2,26),
patka na rámu. Kolize s rámem a nohama násypky žádné (BVH v `concept.py`), jen u ventilu se roura dotýká stojanu nádobky
– přesné vedení u nádobky se dořeší v `sdt_mlyn.py`.

**Otočný kloub:** svislá osa (−1,03; z −2,26), ložisko na y 1,46–1,56, vzpěra do nohy násypky.
**Rameno:** vodorovné, osa **y 1,62**, délka **0,80 m** od osy kloubu k ose hlavy. Na konci koleno dolů,
kužel a **plnicí hlava s límcem a objímkou** (Ø 0,21, spodní hrana **y 1,32**), páčka objímky. Pod hlavou volitelný
uzel **hrdlo vaku** (Ø 0,18, y 1,10–1,33), viditelný jen za plnění.

**Kam s hlavou na vaku:** střed horní plochy vanilla vaku zabírá poutko (do 1,73 m). Hlava proto nesedí nad středem,
ale nad „ramenem“ vaku **0,26 m od středu směrem k vozíku** (tam je látka ve výšce ~1,12 m a poutko je bokem). Vak se staví
natočený tak, aby poutko bylo kolmo k rameni. Díky tomu stačí hlava 0,15–0,20 m nad látkou a celé rameno je o 0,4 m níž
než dnešní ústí – a **nikdy nepřechází přes poutko**.

**Stavy (otáčení kolem svislé osy):**

| stav | úhel | hlava | střed vaku | vůle |
|---|---|---|---|---|
| 1 přeprava | 0° (rameno dopředu podél pravého boku násypky, hlava v opěrce na boku násypky z −1,46) | (−1,03; 1,32; −1,46) | – | v obrysu (x ≥ −1,14) |
| 2 vedle vozíku | −90° (ven vpravo) | (−1,83; 1,32; −2,26) | (−2,09; −2,26) | 0,33 m od kola |
| 3 za vozíkem | −180° (dozadu) | (−1,03; 1,32; −3,06) | (−1,03; −3,32) | 0,29 m od zádě |

**Doporučení: obě polohy, výchozí po prvním O je „vedle“.**
- *Vedle (90°):* k vaku se dá najet čelním nakladačem / manipulátorem kolmo z boku, mlýnek může zůstat zapřažený za Maxem
  (zádí Maxu je oj mlýnku, vedle mlýnku je volno). Vak je v zorném poli z kabiny tahače. Potřebuje volný pruh ~1,9 m
  vpravo – u cesty nebo plotu to nejde.
- *Za vozíkem (180°):* nejméně místa do šířky, nic nekoliduje s tahačem (ten je vpředu); odvoz vaku nakladačem zezadu
  v ose. Když se ale odjíždí, vak musí pryč dřív, jinak se do něj rameno při skládání netrefí – to nehrozí, rameno je výš
  než látka a vak stojí 0,26 m za hlavou.
- Jedna roura, jeden kloub, třetí stav nic nestojí – proto obě.

Rendery: `out/mill_concept/mill_preprava_{top,iso,zezadu}.png`, `mill_90_{top,iso,zezadu}.png`,
`mill_180_{top,iso,zezadu}.png`, detail hlavy nad vakem `mill_detail_head.png` a z boku `mill_detail_head_bok.png`.

## 2. Ventil (rozdělovač) a ovládání

**Rozdělovač:** klapkový dvoucestný kus pod nádobkou jemného vápna (−0,80; 0,70; 0,15): jedna větev dál na
**trvalou spojku Storz** (`millOutletPort` zůstává, hadice vleku se připojuje jako dnes), druhá větev do potrubí k rouře.
Hřídel klapky vede dopředu (z +0,40, před stojan nádobky), na ní **červená páka**: **vodorovně ven = hadice**,
**svisle nahoru = roura** (90°, viditelné zdálky). Rendery `mill_detail_ventil_hadice.png`, `mill_detail_ventil_roura.png`.
Spojka možná půjde o 0,1 m ven (x −1,10), aby ventil neseděl v rámu nádobky – rozhodne stavba.

**Klávesy (sjednocené schéma z `OVLADANI-audit.md`):**

| akce | pěšky | ve vozidle (nastoupený / vybraný z tahače) |
|---|---|---|
| ventil hadice ↔ roura | **levé tl.** na páku ventilu (`ACTIVATE_HANDTOOL`, klik na ovladač, dnešní `SprayDroneMillModeActivatable` přesunutý na uzel páky) | **Y** (`IMPLEMENT_EXTRA3`, beze změny) |
| roura: přeprava → vedle → za → přeprava | **levé tl.** na kloub roury (nový activatable u ložiska) | **O** (`TOGGLE_PIPE`, jako kombajn / překládací vůz) |
| motor | B / levé tl. na tlačítko (beze změny) | B (beze změny) |

Texty akce O podle vanilla: „Vyklopit rouru vedle vozíku“, „Vyklopit rouru za vozík“, „Složit rouru“ (vlastní klíče,
vanilla `action_pipeOut/In` nerozlišují dvě polohy).

**Vanilla `Pipe` spec, nebo vlastní animace? → vlastní animace + akce `TOGGLE_PIPE`.**
`Pipe.lua` má sice O, stavy (`states#num`, cyklus 1→2→3→1 v `actionEventTogglePipe`, ř. 1572–1584), síť a save, ale:
- `Pipe.prerequisitesPresent` chce **Dischargeable** (ř. 19). Mlýnek je `baseFillable` bez Dischargeable; přidat ho
  znamená vanilla vysypávání (paprsek, `dischargeNode`, efekty, AI, zákazy zapnutí `turnOnStateWarning`) jen kvůli
  pohybu roury.
- Vanilla big bag nemá `exactFillRootNode` a mlýnek ho potřebuje sám **stavět** (`spawnBag`) – vlastní přesun
  (`updateBag`) zůstane tak jako tak.
- `addPoweredActionEvent` (ř. 1483): roura by šla jen s nastartovaným tahačem, ne s motorem mlýnku.
Proto: animace `spoutSwing` v `<animations>` (AnimatedVehicle už mlýnek má kvůli opěrnému kolečku), rotace uzlu
`millSpoutPivot` 0 → −180°, ~6 s, zastávky na čase 0 / 0,5 / 1 (`setAnimationStopTime` + `playAnimation`), zvuky
vanilla šablon jako u `moveSupport`; vlastní akce na `InputAction.TOGGLE_PIPE` → O zůstane O.

**Ventil na rouře, roura složená / v pohybu:** tok stojí (mezisklad 150 l se plní dál, dokud není plný), za chodu motoru
bliká hláška „Výsypná roura je složená – vyklop ji (O)“ (`showBlinkingWarning`, jen nastoupenému / u ventilu).
**Ventil na rouře a připojená hadice:** přepnutí se nově **povolí** (hadice je trvalá přípojka), hadice nic nedostane –
pumpa vleku ukáže „Výstup mlýnku je přepnutý na rouru“. Dnešní zákaz `sdt_mill_modeHoseAttached` odpadne.

## 3. Logika (SprayDroneMill) a vznik vaku

Podmínky toku do vaku: motor běží **a** ventil = roura **a** roura ve stavu 2/3 **a** animace stojí **a** vozík stojí
(rychlost < 1 km/h). Vak se hledá a staví **pod hlavou**:
- uzel `millFillHead` (dítě `millSpoutPivot`) nahrazuje `bagOutput#nozzle` – poloha se bere ze světa, takže sedí
  v obou stavech bez přepočtu;
- očekávaný střed vaku = hlava + směr ramene × `bagOutput#neckOffset` (0,26); `findBag` hledá kořen vaku v okruhu
  `halfWidth` 0,6 m kolem tohoto středu a výšce `≤ hlava − 0,8`;
- `spawnBag`: kořen na terénu (`getTerrainHeightAtWorldPos`) + 0,02, natočení = směr ramene + 180° (poutko kolmo
  k rameni). `BAG_SPAWN_DROP` odpadá;
- hrdlo vaku `millBagNeck` se ukáže, když `spec.bag` existuje a fouká se; prach `dust.blowing` se linkuje na `millFillHead`.

**Změny po souborech (odhad):**

| soubor | změna | rozsah |
|---|---|---|
| `blender/sdt_mlyn.py` | rozdělovač + páka, potrubí po palubě, objímky, stoupačka, ložisko, rameno, koleno, hlava s límcem/objímkou, hrdlo vaku, opěrka; spojka možná o 0,1 m ven | ~200 ř. |
| `blender/build_trailer_mill.py` | pivoty `millValveLever`, `millSpoutPivot`, `millFillHead`, `millBagNeck`, `millSpoutJoint` (klik pěšky); fill plane `coarseFillPlane` | ~40 ř. |
| `blender/export_mill_mod.py`, `templates/sdtLimeMill.xml.in` | mapování nových uzlů; `<animation name="spoutSwing">`, `<animation name="valveLever">`; `<bagOutput head="millFillHead" neck="millBagNeck" neckOffset="0.26" halfWidth="0.6"/>` místo `nozzle`/`pipe`; `<fillPlane>` u fill unit 1 | ~50 ř. |
| `blender/build_blowpipe.py`, `objects/limeBigBag/blowPipe.i3d` | do archivu / smazat | – |
| `scripts/SprayDroneMill.lua` | `bagMode` → `valveSpout`, nový `spoutState` (sync 2 bity, save), `CMD_SPOUT_STATE` (CMD_BITS 2 → 3), akce O, activatable kloubu, podmínky toku, `findBag`/`spawnBag` od uzlu hlavy, hláška složené roury, zrušení načítání `blowPipe` | ~180 ř. |
| `scripts/events/SprayDroneMillEvent.lua` | nový příkaz se stavem roury | ~10 ř. |
| `scripts/SprayDroneWaterHose.lua` | text „výstup přepnutý na rouru“ místo odmítnutí | ~10 ř. |
| `translations/translation_*.xml` | `sdt_mill_valveToHose/ToSpout`, `sdt_mill_spoutSide/Rear/Fold`, `sdt_mill_spoutFolded`, `sdt_mill_hoseSpout`; zrušit `modeToBag`, `modeHoseAttached` | 7 klíčů × jazyky |
| `docs/DRON.md`, `OVLADANI-audit.md`, `KONTROLA-body-svetla.md` (+ `out/check_body/scripts/mill_bag.py`) | popis, tabulka kláves, kontrola vůlí ve 3 stavech | – |

## 4. Mobilní násypka: výsypná stolice, zásoba, hladina

**Stolice (big bag discharger):** na ústí lievce (y 1,02) **nástavec** – plechová skříň 0,90 × 0,90 do **y 1,40**,
nahoře dosedací rám z jeklu, čtyři rohové **náběhy** (vodítka, vyhnutá ven do 0,52 / 0,45 od osy, aby vak 0,99 × 0,84
sjel na střed), **mřížka** a **nůž** (dvě zkřížené čepele, špička 0,10 nad rámem – protrhne dno vaku). Rendery
`hopper_stolice_iso.png` (bez vaku), `hopper_vak_iso.png` (s vakem), `hopper_rez_hladina.png` (řez s hladinou).

**Jak vak drží a jak se sype: nic vlastního.** Vak se nakladačem jen **položí** na rám (kořen vaku = dno na y 1,40).
Jeho vanilla `dischargeActivationTrigger` (sahá 3,7 m pod dno) pak překrývá násypku a `Dischargeable` vaku
(`canStartDischargeAutomatically`, paprsek dolů) sám začne sypat do `limeFillRootNode` násypky – přesně tak dnes funguje
ladicí `hopperBigBag` (vak drží 0,5 m nad ústím). Když je násypka plná, sypání se zastaví, a jak hadice vleku ubírá,
pokračuje. `dynamicMount` ani trigger nejsou potřeba; náběhy jen drží vak na místě fyzikou.
`limeFillRootNode` se posune pod mřížku (y ~1,30), `hopperFunnel` (pytle 50 l) na rám (y 1,42).

**Stabilita:** vak 1 000 l nahoře na 80kg násypce s půdorysem 1,0 × 1,26 m se snadno překlopí. Navrhuji **vysouvací
opěry** do 1,6 m šířky (na renderu oranžové), nebo jednodušeji těžší rám (`mass` 80 → 250, `centerOfMass` níž).

**Drobná zásoba:** lievec ~150 l + nástavec (0,33 m užitečné výšky) ~267 l = **≈ 420 l → kapacita fill unit 2 na 400 l**
(dnes 500 l, které se do geometrie nevejdou). Zásoba plní fill unit bez ohledu na motor (sypání vaku i pytlů motor
nepotřebuje), dopravník ji jen vybírá. Chce-li Pavel 500 l, nástavec do y 1,49.

**Viditelné naplnění – vanilla `fillPlane`** (`FillUnit.loadFillPlane`: uzel s rovinou, klíče `time` → `y` + `scale`,
materiál `fillPlane` hra přiřadí sama, textura podle druhu – `SDT_FINE_LIME` už textury a height type má):

| kde | uzel (rovina) | klíče `time: y, scale` |
|---|---|---|
| mobilní násypka, fill unit 2 | `limeFillPlane` v ose lievce (0; ·; 0,22), rovina 0,90 × 0,90 | 0: 0,48 / 0,20 · 0,115: 0,80 / 0,61 · 0,36: 1,02 / 0,89 · 1: 1,35 / 1,0 |
| mlýnek, fill unit 1 (hrubé vápno) | `coarseFillPlane` v ose násypky (0; ·; −1,43), rovina 1,72 × 1,56 | 0: 1,00 / 0,17×0,19 · 0,087: 1,50 / 0,57 · 0,22: 1,76 / 0,77 · 0,44: 2,02 / 0,97 · 0,65: 2,22 / 1 · 0,87: 2,40 / 1 · 1: 2,50 / 1 (kupka) |

Řez s hladinou: `mill_rez_hladina.png`, `hopper_rez_hladina.png`.

**Změny po souborech (násypka):** `blender/build_hopper.py` (nástavec, rám, náběhy, mřížka, nůž, opěry, rovina
`limeFillPlane`, posun `limeFillRootNode` a `hopperFunnel`; ~120 ř.), `objects/hopper/limeHopper.xml` (kapacita 400,
`<fillPlane>`, `size height` 1,1 → 1,45, hmotnost; ~20 ř.), `SprayDroneHopper.lua` beze změny (volitelně jen log
„vak leží na stolici“). Celkem obě části ≈ 2–3 sezení: Blender + export mlýnku je delší (export 25+ min), Lua střední.

## 5. Otevřené otázky pro Pavla

1. Hlava nad „ramenem“ vaku (0,26 m od středu), protože střed zabírá vanilla poutko do 1,73 m – OK, nebo hlavu nad
   střed a rameno nad poutko (pak y ~1,95, skoro jako dnes)?
2. Obě polohy (O: přeprava → vedle → za → přeprava), nebo jen jedna?
3. Ventil na rouru i s připojenou hadicí povolit (hadice nic nedostane), nebo blokovat jako dnes?
4. Rouru pěšky klikem na kloub, nebo jen z vozidla (O)?
5. Násypka: 400 l podle geometrie, nebo vyšší nástavec na 500 l? Opěry, nebo jen těžší rám?
6. Vanilla vak sype `emptySpeed` 100 l/s – násypku naplní za ~4 s a pak dosypává po kouscích. Stačí, nebo zpomalit
   (vlastní limeBigBag.xml už `parentFile` přepisuje, jde přidat `emptySpeed`)?
