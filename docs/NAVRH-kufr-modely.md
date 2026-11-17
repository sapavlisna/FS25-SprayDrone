# Návrh: 3D modely kufrů s drony a baterie jako předměty (F2, F3 z PLAN-airasi-kufr.md)

Stav 2026-10-29: modely jsou vyexportované a mají náhledy, XML a Lua hotové; večer přibyla přistávací podložka a přenos dronu
z pěny na ni (animace víka, níž). Vyrábí je
`blender/build_drone_case.py` (`blender.exe -b --python blender\build_drone_case.py [-- scanCase samplerCase batteries]`),
`.blend` je `blender/spraydrone_drone_case.blend` (oba kufry vedle sebe).
Skript zároveň vypisuje strom uzlů, `i3dMappings` a řádky bloku `<drone>` podle hotového i3d do
`out/case_preview/<jméno>_export.txt` – **čísla v XML berte vždycky odtud**, po každém novém exportu se mohou změnit.

| soubor | obsah |
|---|---|
| `objects/droneCase/scanCase.i3d` (+ `.shapes`, `store_scanCase.dds`) | skenovací sada, dron `Drone_C_` (třída Mavic 3 Multispectral) |
| `objects/droneCase/samplerCase.i3d` (+ `.shapes`, `store_samplerCase.dds`) | AIRASI, dron `Drone_P_` se sondou a bedničkou na vzorky |
| `objects/battery/battery{S,M,L,C,P}.i3d` (+ `store_battery*.dds`) | baterie jako předměty |
| `out/case_preview/*.png` | náhledy (zavřený / otevřený kufr, dron na podložce, průběh animace, dron rozložený zboku a shora, baterie) |

Souřadnice jsou v i3d (Y nahoru, +Z dopředu), úhly ve stupních. Čelo kufru (madlo, přezky, LED) je v i3d na **+Z**
(v Blenderu −Y), panty vzadu (−Z), nabíjecí zásuvka na boku +X.

## Kufry

| | scanCase | samplerCase |
|---|---|---|
| rozměr (d × š × v) | 0,60 × 0,42 × 0,24 m (spodek 0,15, víko 0,09) | 0,80 × 0,55 × 0,30 m (spodek 0,19, víko 0,11) |
| hmotnost (`component mass`) | 12 kg | 25 kg |
| těžiště (návrh) | `0 0.09 0` | `0 0.11 0` |
| přezky a víčko bedničky | červené (BZUK) | oranžové |

Kořen je stejný jako u pumpy a dronových předmětů: `<jméno>_main_component1` (dynamic, compound, group `0x10004`,
mask `0xfffffbff`, density 0) → `collisions/floorCollision01` (kvádr celého ZAVŘENÉHO kufru, group `0x10000`,
mask `0xfffdfbff`). Navíc jako u kanystru `dynamicMountTrigger` (upínání na vlek/auto) a jako u tyče `exactFillRootNode`
(group `0x40000000`, mask `0x20000000` – kdyby se kufr měl nabíjet přes loadTrigger; nepoužitý jde smazat z mapování).

### Uzly kufru (společné)

| uzel | typ | k čemu | výchozí |
|---|---|---|---|
| `<jméno>_vis` | mesh | skořepina, pěna s výřezy, madlo, přezky, panty, zásuvka, rámeček LED | – |
| `caseLid` | TG, pivot v ose pantu | **víko**: animace Foldable, otevřeno = rozloženo. Natočení zavřeno `0 0 0`, otevřeno **`-110 0 0`** (kolem i3d X, víko jde nahoru a dozadu) | zavřeno |
| `caseLid_vis` | mesh pod `caseLid` | víko s pěnou, polep BZUK (`brand_BZUK_caseLidTop`, `brand_BZUK_caseLidFront`) | – |
| `casePad` | TG pod `caseLid`, počátek uprostřed dole | **přistávací podložka** (pružinová obruč s potahem): složená (měřítko `1/3 3 1/3` = stočená do tří vrstev) leží zapuštěná v pěně víka, animace víka ji vyndá, položí na zem vedle kufru (strana −X) a rozevře (měřítko 1) | složená ve víku |
| `casePad_vis` | mesh | kotouč Ø 0,90 m (scanCase) / 1,40 m (samplerCase), oranžový, bílý kruh a H, tmavý lem | – |
| `droneCarrier` | TG, v zavřeném kufru jednotková matice | **nosič dronu**: rodič `<prefix>Root`; animace víka jím přenese dron z pěny na střed H. Domov dronu (`SprayDroneStation.getHomePosition`, rodič kořene) jde s ním | v pěně |
| `caseBatterySlot`, `caseBatterySlot2` | TG | dvě šachty baterií v pěně (počátek = dno baterie); pool `power#slots="2" batteries="2"` i s baterií v dronu | – |
| `caseBattery`, `caseBattery2` | mesh | baterie v šachtě (C / P); skript ji schová, když je šachta prázdná | viditelné |
| `caseChargeCable` | TG + mesh | zástrčka v zásuvce na boku (+X), smotaný kabel na zemi, síťová vidlice | **skrytý** – ukázat při nabíjení |
| `caseChargeLed0..3` | mesh | 4 zelené segmenty indikátoru nabíjení na čele pod madlem (zleva doprava), pod nimi zhasnuté čočky v `_vis` | viditelné |

Pozice v i3d: scanCase `caseLid` t=`0 0.15 -0.217`, zásuvka a `caseChargeCable` t=`0.3 0.072 0.0945`, šachty x −0,08 a −0,215;
samplerCase `caseLid` t=`0 0.153 -0.287` (pant v půlce výšky, 1,2 cm za zadní stěnou), `caseChargeCable` t=`0.4 0.0912 0.12375`,
šachty t=`0.06 0.13 0.165` a `0.28 0.13 0.165`.

Animace víka (`caseLidAnim`, jediný díl Foldable; čas 0 = otevřeno, 1 = zavřeno) je celá sekvence otevření, skript ji vypisuje
hotovou do `out/case_preview/<jméno>_export.txt` (sekce „animace víka…“) podle `CASE_ANIM` a `CASES[...]["anim_s"]` (scanCase 5 s,
samplerCase 6 s). Ve směru zavírání (podíly délky):

| podíl | uzel | co se děje |
|---|---|---|
| 0–0,20 | `droneCarrier` | ramena a listy se skládají (`sprayDrone#trailerFoldEnd="0.2"`); nosič se zvedne o 2 mm, aby animace v tom čase běžela (bez změny hodnoty AnimatedVehicle při rozkládání skočí rovnou na čas 0) |
| 0,20–0,28 | `droneCarrier` | dron se zvedne z podložky (lyžiny 4 cm nad okraj spodku kufru) |
| 0,28–0,43 | `droneCarrier` | přenese se nad výřez v pěně |
| 0,43–0,50 | `droneCarrier` | spustí se do výřezu (nosič na `0 0 0`) |
| 0,50–0,58 | `casePad` | podložka se na zemi složí (měřítko 1 → 1/3, tloušťka ×3) |
| 0,58–0,63 | `casePad` | zvedne se nad zem (H + 0,12 m), vodorovně (rot X +110° vůči otevřenému víku) |
| 0,63–0,70 | `casePad` | přenese se k víku a natočí do jeho roviny (rot X → 0) |
| 0,70–0,75 | `casePad` | zasune se do pěny víka |
| 0,75–1 | `caseLid` | víko se zavře (`-110 0 0` → `0 0 0`) |

Podložka je dítě víka, takže její polohy jsou v rámci **otevřeného** víka a otáčí se jen kolem jeho osy X. Střed rozložené podložky
je na zemi `L/2 + mezera + R` od středu kufru po −X (scanCase 0,81 m, samplerCase 1,18 m); dron na ní míří nosem po +X kufru jako
v pěně, takže přenos je jen posun a `initHomeYawOffset` se nemění. U AIRASI je složená podložka ~5 mm nad nejvyšším bodem dronu.

### Jen samplerCase (AIRASI)

**Kufr na dvě poloviny (2026-10-29 večer):** víko `caseLid` se otevře o **180°** (`-180 0 0`) a leží vnitřkem nahoru na zemi za kufrem
(i3d −Z; pant v půlce výšky H/2 + 3 mm, takže vnější strana víka je 6 mm nad zemí). Bednička se vzorky je ve víkové polovině pod
`caseSampleBox` (TG pod víkem, `180 0 0`, takže při otevřeném víku jsou její osy jako svět a víčko `caseSampleBoxLid` se dál otevírá −100°
kolem X, pant na straně dál od kufru). Složená podložka je v pěně víka vedle bedničky, uložená lícem dolů (`casePad` r=`180 0 0`), po otevření
leží lícem nahoru; animace ji zvedne 0,08 m, přenese ve výšce H + 0,12 m nad místo vedle kufru (−X) a spustí (fáze `padSwing` 0,63–0,67 a
`padDrop` 0,67–0,70, bez otáčení), takže nepřejede nad dronem ani bedničkou. Pěna spodku: dron, dvě baterie P vpředu vpravo; kapsa dronu
jen 4 mm nad dnem (stožárek sondy je pak 4 mm pod složenou podložkou).

**Dron P na nohách:** čtyři skládací nohy `Drone_P_Leg_1..4` (kloub pod trupem na vzpěře, délka 0,42 m, rozložené 12° ven, složené vodorovně
pod trupem: přední dozadu, zadní dopředu, foldPart kolem X ±102° v čase 0,6–1), `Drone_P_Tilt` se při rozložení zvedne o 0,395 m (foldPart
s `foldedTrans`/`unfoldedTrans`), chodidla jsou pak v rovině kořene (= nejnižší bod složeného dronu). Sonda čtyřstupňová v pouzdru, které jde
trupem nahoru jako stožárek (x = +0,08 m od středu trupu): `Drone_P_Probe` → `ProbeMid` → `ProbeMid2` → `ProbeTip`, posuvy 0,18 / 0,18 /
0,18 / 0,19 m (`sampler#probeTravel`, `midTravel`, `tipTravel`); se `sampler#height` 0,02 sahá hrot ~0,31 m pod terén. Náhledy
`samplerCase_drone_sampling_{side,front}.png`, `samplerCase_open_{side,end}.png`.


| uzel | k čemu | výchozí |
|---|---|---|
| `caseSampleBoxLid` (TG, pivot v pantu bedničky) + `caseSampleBoxLid_vis` | víčko bedničky na vzorky: zavřeno `0 0 0`, otevřeno **`-100 0 0`** (kolem X) | zavřeno |
| `caseSamples` → `caseSample1..8` | vzorkovnice v bedničce (2 řady × 4), viditelnost po jedné podle počtu vzorků | **skryté** |

Bednička je 0,32 × 0,165 × 0,11 m s přihrádkami 4 × 2, sedí v pěně vpředu vlevo; baterie P vpředu vpravo.

## Drony

Struktura je **stejná jako u dronů na plošině vleku** (`export_middle_mod.drone_nodes`), takže kufr jde v
`SprayDroneStation` použít jako „plošinu“ s jednou variantou:

```
droneCarrier                 nosič (jen v kufru): animace víka ho přenese na podložku, rodič kořene = domov dronu
<prefix>Root                 kořen (skript ho při vzletu přepojí do světa); r = 0 90 0, viz pozn.
└ <prefix>Tilt               náklon za letu, BEZ natočení (skript píše setRotation(tilt, pitch, 0, roll))
  ├ <prefix>ArmPivot_1..4    kloub ramene, skládá se kolem i3d Y (foldPart)
  │ ├ <prefix>Arm_i          rameno + motor (propSource = Arm_1)
  │ ├ <prefix>Led_i          čočka poziční LED (SDT_NavLed, barva ve vrcholech) └ <prefix>LedLight_i (bodové světlo)
  │ └ <prefix>Rotor_iTop     rotor, BEZ natočení vůči kloubu (skript: setRotation(rotor, 0, úhel, 0))
  │   ├ <prefix>Blade_iTop0/1   skládací list (foldPart kolem Y) └ _Tip (proužek, propBlade tip)
  │   └ <prefix>Hub_i
  ├ <prefix>BatterySlot      lůžko baterie v trupu └ <prefix>Battery (mesh, schovat při vytažení)
  └ <prefix>Body             trup se vším pevným (kamera, nohy/lyžiny)
```

Číslování ramen jako u vleku: 1 vpředu vlevo (červená LED), 2 vpředu vpravo (zelená), 3 a 4 vzadu (bílá, blikají);
směr rotorů 1: `1`, 2: `-1`, 3: `-1`, 4: `1`. `FillPort` drony nemají (nemají nádrž; `SprayDroneService` s chybějícím
hrdlem počítá – `port = nil`, hadice se nenačte). Spray efekty/trysky vynechat.

**Natočení kořene.** Nos dronu je v `<prefix>Tilt` na +Z jako u vleku, ale dron leží v kufru podélně, takže
`<prefix>Root` má v i3d `r = 0 90 0` (nos míří na i3d +X kufru). `SprayDroneStation` si při načtení bere `localRot`
kořene a při parkování ho vrací, takže by to mělo projít; kdyby domovská orientace (`initHomeYawOffset`) dělala potíže,
je to první místo, kam se podívat.

### Rozložení ramen a listů

Ramena se skládají vodorovně kolem svislé osy (i3d **Y**) jako u Agrasů – zjednodušení: skutečný Mavic má zadní ramena
na šikmé ose. Složená ramena leží podél boků trupu ve dvou výškách (přední výš, zadní níž), takže se nekříží; listy
složené míří po rameni ven (±2°), rozložené napříč ramene (±90°). Hodnoty z i3d (`foldedRot` = stav v i3d):

| uzel | Drone_C_ foldedRot → unfoldedRot | Drone_P_ foldedRot → unfoldedRot | čas |
|---|---|---|---|
| ArmPivot_1 | `0 79.605 0` → `0 -40.121 0` | `0 80.188 0` → `0 -42.274 0` | 0–0,6 |
| ArmPivot_2 | `0 100.395 0` → `0 220.121 0` | `0 99.812 0` → `0 222.274 0` | 0–0,6 |
| ArmPivot_3 | `0 -78.319 0` → `0 36.769 0` | `0 -80.188 0` → `0 42.274 0` | 0–0,6 |
| ArmPivot_4 | `0 -101.681 0` → `0 -216.769 0` | `0 -99.812 0` → `0 -222.274 0` | 0–0,6 |
| Blade_iTop0 | `0 2 0` → `0 90 0` | totéž | 0,5–1 |
| Blade_iTop1 | `0 -2 0` → `0 -90 0` | totéž | 0,5–1 |

Úhly ramen nejsou „hezká“ čísla, protože v nich je i otočení nosu (−90°); interpolace je lineární a směr pohybu
(ven od trupu, ne skrz) je zaručený tím, jak skript počítá rozdíl.

### Drone_C_ (skenovací, třída Mavic 3M)

- Rozložený: rozteč motorů 0,26 × 0,27 m (úhlopříčka **0,375 m**), vrtule 0,236 m (9,4″), výška 0,12 m.
- Složený: cca 0,33 × 0,17 × 0,12 m (listy přesahují trup dopředu a dozadu).
- Na trupu: kardan pod nosem s hlavou se **4 multispektrálními čočkami a RGB** uprostřed, **sluneční senzor** (bílý
  difuzor) na hřbetě, překážkové senzory vpředu a vzadu, čtyři nožky. Baterie C vzadu nahoře (`Drone_C_Battery`).
- `Drone_C_Tilt` 0,07 m nad zemí.

### Drone_P_ (AIRASI, vzorkovač)

- Rozložený: rozteč motorů 0,50 × 0,49 m (úhlopříčka **0,70 m**), vrtule 0,38 m, 4 rotory, výška ~0,23 m.
- Bílý trup s oranžovými pruhy, karbonová ramena, dvě lyžiny, kamera pod nosem, baterie P na hřbetě.
- Nohy a čtyřstupňová sonda: viz „Jen samplerCase (AIRASI)“ výš; následující dvoustupňová sonda a lyžiny jsou PŮVODNÍ stav.
- **Sonda** pod trupem (pevné pouzdro je v `Drone_P_Body`), dvoustupňová teleskopická:
  - `Drone_P_Probe` (vnější trubka): t=`0 0.055 0` → vysunuto `0 -0.085 0` (posuv **−0,14** po Y)
  - `Drone_P_ProbeTip` (hrot, dítě Probe): t=`0 -0.01 0` → vysunuto `0 -0.17 0` (posuv **−0,16** po Y)
  - dohromady 0,30 m; hrot zasunuté sondy je 2 cm nad zemí, vysunuté ~0,28 m pod povrchem. Pro jednu animaci stačí
    pohnout oběma uzly ve stejném čase; kdo chce jen jeden uzel, posune `Drone_P_Probe` a hrot zůstane zasunutý (0,14 m).
- **Držák vzorků** `Drone_P_SampleHolder` pod zádí → `Drone_P_Sample1`, `Drone_P_Sample2` (vzorkovnice, **skryté**,
  ukazuje je skript po odběru).
- `Drone_P_Tilt` 0,16 m nad zemí.

### Navržený blok `<drone>` do XML kufru

Parametry letu jsou návrh (Mavic 3M: 951 g, baterie 77 Wh, 43 min; AIRASI odhad); uzlové řádky jsou přesně z
`out/case_preview/scanCase_export.txt`, sekce `drone block parts`.

```xml
<drone name="C" prefix="Drone_C_" scan="true" scanSpeed="12" scanMaxWind="12" maxRange="500" tankCapacity="0" litersPerSecond="0"
       workWidth="6" droneMass="0.6" batteryMass="0.35" batteryKwh="0.077" batteryMinutes="40" chargeMinutes="60"
       droneRadius="0.32" rotorPitch="2.2">
    <sounds>
        <rotor file="sounds/droneRotorLoop.ogg" linkNode="Drone_C_Tilt" innerRadius="3" outerRadius="60" fadeOut="0.3">
            <volume indoor="0.3" outdoor="0.6"/><pitch indoor="1" outdoor="1"/><lowpassGain indoor="0.6" outdoor="1"/>
        </rotor>
    </sounds>
    <tilt node="Drone_C_Tilt"/>
    <foldPart node="Drone_C_ArmPivot_1" foldedRot="0.000 79.605 0.000" unfoldedRot="0.000 -40.121 0.000" startTime="0" endTime="0.6"/>
    <foldPart node="Drone_C_Blade_1Top0" foldedRot="0.000 2.000 0.000" unfoldedRot="0.000 90.000 0.000" startTime="0.5" endTime="1"/>
    <foldPart node="Drone_C_Blade_1Top1" foldedRot="0.000 -2.000 0.000" unfoldedRot="0.000 -90.000 0.000" startTime="0.5" endTime="1"/>
    <!-- … ramena 2–4 a jejich listy podle tabulky výš / export.txt … -->
    <propSource node="Drone_C_Arm_1"/>
    <propBlade node="Drone_C_Blade_1Top0" tip="Drone_C_Blade_1Top0_Tip"/>  <!-- … 8 listů … -->
    <rotor node="Drone_C_Rotor_1Top" direction="1"/>
    <rotor node="Drone_C_Rotor_2Top" direction="-1"/>
    <rotor node="Drone_C_Rotor_3Top" direction="-1"/>
    <rotor node="Drone_C_Rotor_4Top" direction="1"/>
    <navLight node="Drone_C_Led_1" lightNode="Drone_C_LedLight_1" blink="false"/>
    <navLight node="Drone_C_Led_2" lightNode="Drone_C_LedLight_2" blink="false"/>
    <navLight node="Drone_C_Led_3" lightNode="Drone_C_LedLight_3" blink="true"/>
    <navLight node="Drone_C_Led_4" lightNode="Drone_C_LedLight_4" blink="true"/>
</drone>
```

AIRASI analogicky s `name="P" prefix="Drone_P_"` (bez `scan`, např. `droneMass="4.5" batteryMass="1.1" batteryKwh="0.2"
batteryMinutes="25" droneRadius="0.55" rotorPitch="1.6"`) a s uzly z `samplerCase_export.txt`; sonda a vzorky jsou nové
uzly mimo dnešní schéma (`sampler` blok si navrhne kód F3). Vlek měl `PROPELLER_DEFAULTS` jen pro S/M/L – pro C a P
vrtule spadnou na výchozí M (tmavé listy bez proužků), což oběma sedí.

## Baterie jako předměty (`objects/battery/`)

S/M/L jsou **tvarově shodné s bateriemi ve vlecích Middle a Max** (obě staví `sdt_parts.battery`, rozměry
`sdt_parts.BATTERY_SIZES`, barva pruhu S modrá / M oranžová / L červená, madlo na čele +X už v modelu je). C a P jsou
baterie kufrových dronů (C ~ Mavic Intelligent Flight Battery, P s poutkem nahoře).

| předmět | rozměr těla (d × š × v) | celkově s madlem | hmotnost | pruh |
|---|---|---|---|---|
| batteryS (DB800) | 0,30 × 0,19 × 0,11 | 0,349 × 0,200 × 0,119 | 6,6 kg | modrý |
| batteryM (DB1560) | 0,37 × 0,23 × 0,13 | 0,421 × 0,240 × 0,139 | 12,1 kg | oranžový |
| batteryL (DB2160) | 0,41 × 0,25 × 0,145 | 0,463 × 0,260 × 0,154 | 14,7 kg | červený |
| batteryC | 0,115 × 0,075 × 0,045 | 0,120 × 0,080 × 0,048 | 0,35 kg | modrý |
| batteryP | 0,19 × 0,095 × 0,06 | 0,194 × 0,100 × 0,086 | 1,1 kg | oranžový |

Strom (stejný pro všech pět, počátek uprostřed dole):

```
battery<K>_main_component1   (dynamic compound, kolize jako pumpa)   0>
├ batteryLed0..3             4 segmenty ukazatele nabití (zelené, samostatně skrývatelné; pod nimi zhasnuté čočky)  0>0..0>3
├ battery<K>_vis             tělo                                      0>4
└ collisions/floorCollision01                                          0>5|0
```

Štítky S/M/L (materiál `SDT_Decal`) berou atlas `../../vehicles/sprayDroneTrailerMiddle/textures/sdt_decals.dds` jako
vlek. Mapování: `out/case_preview/battery<K>_export.txt`.

## Co skript ověřuje a co ne

- Export prošel u všech sedmi i3d, všechny mapované uzly v i3d existují (`X.i3d_mappings` jinak spadne), skryté uzly
  (`caseChargeCable`, vzorky) mají `visibility="false"`.
- Náhledy: `out/case_preview/{scanCase,samplerCase}_{deployed,deployed_top,deployed_side,closed,closed_back,open,open_top,
  drone_unfolded,drone_unfolded_top,drone_unfolded_side,drone_folded_top}.png`, průběh animace `<jméno>_anim_<čas v %>.png`
  (10, 24, 36, 47, 55, 62, 67, 73, 85), `battery*_preview.png`, `store_*.png` (obchod: otevřeno, dron rozložený na podložce).
- Podložka nemá kolizi (dron i hráč jí procházejí); leží v rovině dna kufru, na svahu tedy kopíruje kufr, ne terén.
- **Neověřeno ve hře.** Kolize víka není (kolize je kvádr zavřeného kufru). Složená ramena se při pohledu shora kříží
  (jsou ve dvou výškách, neprotínají se). Zvuk rotoru malých dronů bude chtít vyšší `rotorPitch`.

## i3dMappings (stav exportu 2026-10-29)

### scanCase

```xml
    <i3dMappings>
        <i3dMapping id="scanCase_main_component1" node="0>"/>
        <i3dMapping id="scanCase_vis" node="0>12"/>
        <i3dMapping id="floorCollision01" node="0>8|0"/>
        <i3dMapping id="dynamicMountTrigger" node="0>10"/>
        <i3dMapping id="exactFillRootNode" node="0>11"/>
        <i3dMapping id="caseLid" node="0>7"/>
        <i3dMapping id="caseLid_vis" node="0>7|2"/>
        <i3dMapping id="casePad" node="0>7|3"/>
        <i3dMapping id="casePad_vis" node="0>7|3|0"/>
        <i3dMapping id="droneCarrier" node="0>9"/>
        <i3dMapping id="caseBatterySlot" node="0>0"/>
        <i3dMapping id="caseBattery" node="0>0|0"/>
        <i3dMapping id="caseBatterySlot2" node="0>1"/>
        <i3dMapping id="caseBattery2" node="0>1|0"/>
        <i3dMapping id="caseChargeCable" node="0>2"/>
        <i3dMapping id="caseChargeLed0" node="0>3"/>
        <i3dMapping id="caseChargeLed1" node="0>4"/>
        <i3dMapping id="caseChargeLed2" node="0>5"/>
        <i3dMapping id="caseChargeLed3" node="0>6"/>
        <i3dMapping id="Drone_C_Root" node="0>9|0"/>
        <i3dMapping id="Drone_C_Tilt" node="0>9|0|0"/>
        <i3dMapping id="Drone_C_Body" node="0>9|0|0|5"/>
        <i3dMapping id="Drone_C_BatterySlot" node="0>9|0|0|4"/>
        <i3dMapping id="Drone_C_Battery" node="0>9|0|0|4|0"/>
        <i3dMapping id="Drone_C_ArmPivot_1" node="0>9|0|0|0"/>
        <i3dMapping id="Drone_C_ArmPivot_2" node="0>9|0|0|1"/>
        <i3dMapping id="Drone_C_ArmPivot_3" node="0>9|0|0|2"/>
        <i3dMapping id="Drone_C_ArmPivot_4" node="0>9|0|0|3"/>
        <i3dMapping id="Drone_C_Arm_1" node="0>9|0|0|0|0"/>
        <i3dMapping id="Drone_C_Arm_2" node="0>9|0|0|1|0"/>
        <i3dMapping id="Drone_C_Arm_3" node="0>9|0|0|2|0"/>
        <i3dMapping id="Drone_C_Arm_4" node="0>9|0|0|3|0"/>
        <i3dMapping id="Drone_C_Rotor_1Top" node="0>9|0|0|0|2"/>
        <i3dMapping id="Drone_C_Rotor_2Top" node="0>9|0|0|1|2"/>
        <i3dMapping id="Drone_C_Rotor_3Top" node="0>9|0|0|2|2"/>
        <i3dMapping id="Drone_C_Rotor_4Top" node="0>9|0|0|3|2"/>
        <i3dMapping id="Drone_C_Blade_1Top0" node="0>9|0|0|0|2|0"/>
        <i3dMapping id="Drone_C_Blade_1Top0_Tip" node="0>9|0|0|0|2|0|0"/>
        <i3dMapping id="Drone_C_Blade_1Top1" node="0>9|0|0|0|2|1"/>
        <i3dMapping id="Drone_C_Blade_1Top1_Tip" node="0>9|0|0|0|2|1|0"/>
        <i3dMapping id="Drone_C_Blade_2Top0" node="0>9|0|0|1|2|0"/>
        <i3dMapping id="Drone_C_Blade_2Top0_Tip" node="0>9|0|0|1|2|0|0"/>
        <i3dMapping id="Drone_C_Blade_2Top1" node="0>9|0|0|1|2|1"/>
        <i3dMapping id="Drone_C_Blade_2Top1_Tip" node="0>9|0|0|1|2|1|0"/>
        <i3dMapping id="Drone_C_Blade_3Top0" node="0>9|0|0|2|2|0"/>
        <i3dMapping id="Drone_C_Blade_3Top0_Tip" node="0>9|0|0|2|2|0|0"/>
        <i3dMapping id="Drone_C_Blade_3Top1" node="0>9|0|0|2|2|1"/>
        <i3dMapping id="Drone_C_Blade_3Top1_Tip" node="0>9|0|0|2|2|1|0"/>
        <i3dMapping id="Drone_C_Blade_4Top0" node="0>9|0|0|3|2|0"/>
        <i3dMapping id="Drone_C_Blade_4Top0_Tip" node="0>9|0|0|3|2|0|0"/>
        <i3dMapping id="Drone_C_Blade_4Top1" node="0>9|0|0|3|2|1"/>
        <i3dMapping id="Drone_C_Blade_4Top1_Tip" node="0>9|0|0|3|2|1|0"/>
        <i3dMapping id="Drone_C_Led_1" node="0>9|0|0|0|1"/>
        <i3dMapping id="Drone_C_LedLight_1" node="0>9|0|0|0|1|0"/>
        <i3dMapping id="Drone_C_Led_2" node="0>9|0|0|1|1"/>
        <i3dMapping id="Drone_C_LedLight_2" node="0>9|0|0|1|1|0"/>
        <i3dMapping id="Drone_C_Led_3" node="0>9|0|0|2|1"/>
        <i3dMapping id="Drone_C_LedLight_3" node="0>9|0|0|2|1|0"/>
        <i3dMapping id="Drone_C_Led_4" node="0>9|0|0|3|1"/>
        <i3dMapping id="Drone_C_LedLight_4" node="0>9|0|0|3|1|0"/>
        <i3dMapping id="brand_BZUK_caseLidFront" node="0>7|0"/>
        <i3dMapping id="brand_BZUK_caseLidTop" node="0>7|1"/>
    </i3dMappings>
```

### samplerCase

```xml
    <i3dMappings>
        <i3dMapping id="samplerCase_main_component1" node="0>"/>
        <i3dMapping id="samplerCase_vis" node="0>12"/>
        <i3dMapping id="floorCollision01" node="0>8|0"/>
        <i3dMapping id="dynamicMountTrigger" node="0>10"/>
        <i3dMapping id="exactFillRootNode" node="0>11"/>
        <i3dMapping id="caseLid" node="0>7"/>
        <i3dMapping id="caseLid_vis" node="0>7|2"/>
        <i3dMapping id="casePad" node="0>7|3"/>
        <i3dMapping id="casePad_vis" node="0>7|3|0"/>
        <i3dMapping id="droneCarrier" node="0>9"/>
        <i3dMapping id="caseBatterySlot" node="0>0"/>
        <i3dMapping id="caseBattery" node="0>0|0"/>
        <i3dMapping id="caseBatterySlot2" node="0>1"/>
        <i3dMapping id="caseBattery2" node="0>1|0"/>
        <i3dMapping id="caseChargeCable" node="0>2"/>
        <i3dMapping id="caseChargeLed0" node="0>3"/>
        <i3dMapping id="caseChargeLed1" node="0>4"/>
        <i3dMapping id="caseChargeLed2" node="0>5"/>
        <i3dMapping id="caseChargeLed3" node="0>6"/>
        <i3dMapping id="caseSampleBoxLid" node="0>7|4|0"/>
        <i3dMapping id="caseSamples" node="0>7|4|2"/>
        <i3dMapping id="caseSample1" node="0>7|4|2|0"/>
        <i3dMapping id="caseSample2" node="0>7|4|2|1"/>
        <i3dMapping id="caseSample3" node="0>7|4|2|2"/>
        <i3dMapping id="caseSample4" node="0>7|4|2|3"/>
        <i3dMapping id="caseSample5" node="0>7|4|2|4"/>
        <i3dMapping id="caseSample6" node="0>7|4|2|5"/>
        <i3dMapping id="caseSample7" node="0>7|4|2|6"/>
        <i3dMapping id="caseSample8" node="0>7|4|2|7"/>
        <i3dMapping id="Drone_P_Root" node="0>9|0"/>
        <i3dMapping id="Drone_P_Tilt" node="0>9|0|0"/>
        <i3dMapping id="Drone_P_Body" node="0>9|0|0|5"/>
        <i3dMapping id="Drone_P_BatterySlot" node="0>9|0|0|4"/>
        <i3dMapping id="Drone_P_Battery" node="0>9|0|0|4|0"/>
        <i3dMapping id="Drone_P_ArmPivot_1" node="0>9|0|0|0"/>
        <i3dMapping id="Drone_P_ArmPivot_2" node="0>9|0|0|1"/>
        <i3dMapping id="Drone_P_ArmPivot_3" node="0>9|0|0|2"/>
        <i3dMapping id="Drone_P_ArmPivot_4" node="0>9|0|0|3"/>
        <i3dMapping id="Drone_P_Arm_1" node="0>9|0|0|0|0"/>
        <i3dMapping id="Drone_P_Arm_2" node="0>9|0|0|1|0"/>
        <i3dMapping id="Drone_P_Arm_3" node="0>9|0|0|2|0"/>
        <i3dMapping id="Drone_P_Arm_4" node="0>9|0|0|3|0"/>
        <i3dMapping id="Drone_P_Rotor_1Top" node="0>9|0|0|0|2"/>
        <i3dMapping id="Drone_P_Rotor_2Top" node="0>9|0|0|1|2"/>
        <i3dMapping id="Drone_P_Rotor_3Top" node="0>9|0|0|2|2"/>
        <i3dMapping id="Drone_P_Rotor_4Top" node="0>9|0|0|3|2"/>
        <i3dMapping id="Drone_P_Blade_1Top0" node="0>9|0|0|0|2|0"/>
        <i3dMapping id="Drone_P_Blade_1Top0_Tip" node="0>9|0|0|0|2|0|0"/>
        <i3dMapping id="Drone_P_Blade_1Top1" node="0>9|0|0|0|2|1"/>
        <i3dMapping id="Drone_P_Blade_1Top1_Tip" node="0>9|0|0|0|2|1|0"/>
        <i3dMapping id="Drone_P_Blade_2Top0" node="0>9|0|0|1|2|0"/>
        <i3dMapping id="Drone_P_Blade_2Top0_Tip" node="0>9|0|0|1|2|0|0"/>
        <i3dMapping id="Drone_P_Blade_2Top1" node="0>9|0|0|1|2|1"/>
        <i3dMapping id="Drone_P_Blade_2Top1_Tip" node="0>9|0|0|1|2|1|0"/>
        <i3dMapping id="Drone_P_Blade_3Top0" node="0>9|0|0|2|2|0"/>
        <i3dMapping id="Drone_P_Blade_3Top0_Tip" node="0>9|0|0|2|2|0|0"/>
        <i3dMapping id="Drone_P_Blade_3Top1" node="0>9|0|0|2|2|1"/>
        <i3dMapping id="Drone_P_Blade_3Top1_Tip" node="0>9|0|0|2|2|1|0"/>
        <i3dMapping id="Drone_P_Blade_4Top0" node="0>9|0|0|3|2|0"/>
        <i3dMapping id="Drone_P_Blade_4Top0_Tip" node="0>9|0|0|3|2|0|0"/>
        <i3dMapping id="Drone_P_Blade_4Top1" node="0>9|0|0|3|2|1"/>
        <i3dMapping id="Drone_P_Blade_4Top1_Tip" node="0>9|0|0|3|2|1|0"/>
        <i3dMapping id="Drone_P_Led_1" node="0>9|0|0|0|1"/>
        <i3dMapping id="Drone_P_LedLight_1" node="0>9|0|0|0|1|0"/>
        <i3dMapping id="Drone_P_Led_2" node="0>9|0|0|1|1"/>
        <i3dMapping id="Drone_P_LedLight_2" node="0>9|0|0|1|1|0"/>
        <i3dMapping id="Drone_P_Led_3" node="0>9|0|0|2|1"/>
        <i3dMapping id="Drone_P_LedLight_3" node="0>9|0|0|2|1|0"/>
        <i3dMapping id="Drone_P_Led_4" node="0>9|0|0|3|1"/>
        <i3dMapping id="Drone_P_LedLight_4" node="0>9|0|0|3|1|0"/>
        <i3dMapping id="Drone_P_Probe" node="0>9|0|0|10"/>
        <i3dMapping id="Drone_P_ProbeMid" node="0>9|0|0|10|0"/>
        <i3dMapping id="Drone_P_ProbeMid2" node="0>9|0|0|10|0|0"/>
        <i3dMapping id="Drone_P_ProbeTip" node="0>9|0|0|10|0|0|1"/>
        <i3dMapping id="Drone_P_SampleHolder" node="0>9|0|0|11"/>
        <i3dMapping id="Drone_P_Sample1" node="0>9|0|0|11|0"/>
        <i3dMapping id="Drone_P_Sample2" node="0>9|0|0|11|1"/>
        <i3dMapping id="Drone_P_Leg_1" node="0>9|0|0|6"/>
        <i3dMapping id="Drone_P_Leg_2" node="0>9|0|0|7"/>
        <i3dMapping id="Drone_P_Leg_3" node="0>9|0|0|8"/>
        <i3dMapping id="Drone_P_Leg_4" node="0>9|0|0|9"/>
        <i3dMapping id="brand_BZUK_caseLidFront" node="0>7|0"/>
        <i3dMapping id="brand_BZUK_caseLidTop" node="0>7|1"/>
    </i3dMappings>
```

### batteryS

```xml
    <i3dMappings>
        <i3dMapping id="batteryS_main_component1" node="0&gt;"/>
        <i3dMapping id="batteryS_vis" node="0&gt;4"/>
        <i3dMapping id="floorCollision01" node="0&gt;5|0"/>
        <i3dMapping id="batteryLed0" node="0&gt;0"/>
        <i3dMapping id="batteryLed1" node="0&gt;1"/>
        <i3dMapping id="batteryLed2" node="0&gt;2"/>
        <i3dMapping id="batteryLed3" node="0&gt;3"/>
    </i3dMappings>
```

### batteryM

```xml
    <i3dMappings>
        <i3dMapping id="batteryM_main_component1" node="0&gt;"/>
        <i3dMapping id="batteryM_vis" node="0&gt;4"/>
        <i3dMapping id="floorCollision01" node="0&gt;5|0"/>
        <i3dMapping id="batteryLed0" node="0&gt;0"/>
        <i3dMapping id="batteryLed1" node="0&gt;1"/>
        <i3dMapping id="batteryLed2" node="0&gt;2"/>
        <i3dMapping id="batteryLed3" node="0&gt;3"/>
    </i3dMappings>
```

### batteryL

```xml
    <i3dMappings>
        <i3dMapping id="batteryL_main_component1" node="0&gt;"/>
        <i3dMapping id="batteryL_vis" node="0&gt;0"/>
        <i3dMapping id="floorCollision01" node="0&gt;5|0"/>
        <i3dMapping id="batteryLed0" node="0&gt;1"/>
        <i3dMapping id="batteryLed1" node="0&gt;2"/>
        <i3dMapping id="batteryLed2" node="0&gt;3"/>
        <i3dMapping id="batteryLed3" node="0&gt;4"/>
    </i3dMappings>
```

### batteryC

```xml
    <i3dMappings>
        <i3dMapping id="batteryC_main_component1" node="0&gt;"/>
        <i3dMapping id="batteryC_vis" node="0&gt;0"/>
        <i3dMapping id="floorCollision01" node="0&gt;5|0"/>
        <i3dMapping id="batteryLed0" node="0&gt;1"/>
        <i3dMapping id="batteryLed1" node="0&gt;2"/>
        <i3dMapping id="batteryLed2" node="0&gt;3"/>
        <i3dMapping id="batteryLed3" node="0&gt;4"/>
    </i3dMappings>
```

### batteryP

```xml
    <i3dMappings>
        <i3dMapping id="batteryP_main_component1" node="0&gt;"/>
        <i3dMapping id="batteryP_vis" node="0&gt;4"/>
        <i3dMapping id="floorCollision01" node="0&gt;5|0"/>
        <i3dMapping id="batteryLed0" node="0&gt;0"/>
        <i3dMapping id="batteryLed1" node="0&gt;1"/>
        <i3dMapping id="batteryLed2" node="0&gt;2"/>
        <i3dMapping id="batteryLed3" node="0&gt;3"/>
    </i3dMappings>
```
