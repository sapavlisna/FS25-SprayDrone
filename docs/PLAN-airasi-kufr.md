# Plán: přenosný skenovací dron, vzorkovací dron AIRASI a opravy (2026-10-29)

Zadání (Pavel, 2026-10-29): AIRASI odebírá vzorky půdy (1–2 na let), nosí je na základnu do bedničky, odesílají se jako
u ISARIA. Skenovací dron je malý, přenosný (kufřík, pickup), vzlétá odkudkoli, ovládá se koupeným tabletem a skenuje jen
to, co dnešní drony umí. Vzlet jen z volného místa. Hnojivo / herbicid / vápno různé barvy spreje. Výsyp jemného vápna
jako vápno, ne obilí; hadice na vápno bílá. Dron z Middle/Max jde sundat i z rozloženého vleku (složí se a je z něj
předmět), u Mini jen z rozloženého; Mini v obchodě složený. Drony ve vlastní kategorii obchodu.

## Ověřeno ve hře (2026-10-29, slot 11)

- PF API vzorků z cizího kódu funguje: `DensityMapCircle.new():updateFromWorldPosition(x, z, 32.5, 20)`,
  `pf.coverMap:analyseArea(kruh, nil, farmId, farmlandId)` (= odběr), `pf.soilMap:analyseSoilSamples(farmId, n)`
  (= odeslání, `pendingSoilSamplesPerFarm[farmId]` toAnalyse/totalAnalysed/timer 5000 ms na vzorek, platí se po
  analýze). `soilMap:getPricePerSoilSample()` = 50, `getNumSoilSamplesPerHa()` ≈ 5,2. `coverMap:getIsUncoveredAtPos`,
  `getFarmlandSampleState` existují. Ladění: `pfSoil`, `pfSample`, `pfSend` v SprayDroneDebug.
- `SoilMap.sendSoilSamplesByFarm` prochází jen vozidla se SoilSampler (FS22 zdroj) – naše vzorky odesíláme sami.

## Fáze

**F1 – opravy (nezávislé):**
1. Barvy spreje: `MIST_COLORS` v SprayDroneStation (+ alfa jako hustota), vápno bílé husté, herbicid modrý, hnojivo zelené.
2. SDT_FINE_LIME dostane `<textures>` vanilla LIME (xml/fillTypes.xml) → výsyp big bagu, plochy a prach jako vápno.
3. Hadice na vápno bílá: materiál `SDT_HoseWhite` v build/export skriptech Max a Middle, re-export.
4. Kontrola volného prostoru před vzletem (nový `SprayDroneLaunch.lua`: 17 svislých `raycastAll` nahoru + overlap, ignoruje
   vlastní soupravu; klient při startu, server před každou dávkou – čeká a zkouší znovu jako u relé).
5. Sundání dronu z rozloženého vleku (Middle/Max: dron se složí, pak je předmět), Mini jen rozložený; Mini v obchodě
   složený; drony (a baterie, tablet) ve vlastní kategorii obchodu.

**F2 – přenosný skenovací dron (kufr):** kufr = malé vozidlo (`pallet` + foldable víko + SprayDroneStation v profilu
`portable`: bez Enterable, centrály, mixéru, hadic); víko = rozložení; domov = kufr; tablet ho najde sám (`collectTrailers`).
Nový malý dron (třída Mavic) v Blenderu. Sken bez pH a vápna (jen plevel, růst/zralost, plodina, kameny na holé půdě,
vitalita/N z porostu); vápnění podle skenu bere pH jen z PF tam, kde je odkryté (`coverMap:getIsUncoveredAtPos`).

**F3 – AIRASI:** druhý kufr s variantou `sampler`, mise = body (mřížka podle `getNumSoilSamplesPerHa`, bez už odebraných),
1–2 vzorky na let, odběr = sestup + `analyseArea`, bednička v kufru, „Odeslat“ u kufru i v tabletu → `analyseSoilSamples`.
Bez PF se v obchodě nenabízí.

**F4 – baterie jako předměty (Pavel 2026-10-29):** baterie jde z šachty nabíječky vleku vytáhnout (předmět s nabitím
a velikostí S/M/L), odnést, uložit jinam (na zem, korbu, do jiného vleku nebo kufru) a vrátit; baterie jde koupit
samostatně v obchodě (kategorie Drony). Vzor slot ↔ předmět jako RelaySlots / PumpSlots / PadSlots; pool
`spec.batteries` (`level`, `slot`, `drone`) zůstává, šachta je slot. Konfigurace počtu baterií v obchodě vleku:
zvážit, zda zůstane (předplněné šachty), nebo vlek přijde prázdný. Kufr F2/F3 má šachty pro baterie stejně.

## Stav (2026-10-29 odpoledne, necommitnuto)

Ověřeno ve hře ladicími příkazy (slot 11): kontrola vzletu (volno na poli, „roof“ u budov farmy, překážka u Maxu 7 m od
kufru); skenovací kufr – otevření víka, sken pole 23 (138 buněk), návrat; AIRASI – 8 vzorků po 2 na let, plná bednička
(status 29), odeslání do PF laboratoře a rozbor; baterie – vyndání z šachty Maxu jako předmět, vybíjení baterie kufru.
Ve hře neověřeno: barvy spreje, bílá hadice, výsyp jemného vápna, sundání dronu z rozloženého vleku a Mini, obchod
(kategorie Drony, Mini složený – obrázek store_sprayDroneTrailerMini.dds je starý), nabíjení kufru u budovy/centrály,
R pěšky u šachet a kufru, uložení/načtení, MP. Kosmetika: kufr hlásí stav „na vleku“.

**F5 – dolet kufrových dronů a antény (Pavel 2026-10-29):** oba kufrové drony mají menší dolet (rádio kufru), takže
se pole buď objede (kufr se přenese blíž), nebo se dosah zvedne anténou. Anténa (předmět ke kufru, kupuje se zvlášť,
připojí se ke kufru / postaví vedle; základ bez antény: sken 500 m, AIRASI 400 m – potvrdil Pavel): **všesměrová** (dosah ×1,5) nebo **směrová**
(pokrytí výseč ~99°, dosah ×1,75 – původně ×2,5, snížil Pavel; směr = jak hráč anténu natočí). Plánovač musí počítat dosah i s výsečí (body/pruhy
mimo výseč = mimo dosah) a ukázat ho na mapě. Relé tyče dál fungují. **Antény na stativu Pavel 2026-10-29 zrušil: místo nich směrová relé tyč (kopie relé tyče s panelem,
jen výseč 99°, dosah 1,75× poloměru tyče), viz docs/DRON.md „Směrová relé tyč“. NEOTESTOVÁNO ve hře.**

## Rozhodnutí (D1, D2, D3, D5 potvrdil Pavel 2026-10-29)

- D1 nabíjení přenosného dronu (upřesnil Pavel 2026-10-29): baterie je součástí kufru (šachta v kufru, vyjímatelná jako
  předmět F4) a nabíjí se „ze zásuvky“: kufr leží do ~15 m od budovy farmy (vlastněný placeable s budovou), u běžící
  elektrocentrály (centrála vleku Middle/Max, případně placeable generátor) – klasika, ne kouzlem v zavřeném kufru.
  Bez zdroje se nenabíjí; HUD u kufru ukáže stav a zdroj.
- D2 skenovací dron je jen kufrová sada; varianta K na vlecích zaniká.
- D3 kufr se prodává jako sada (kufr + dron + baterie).
- D5 AIRASI jen s PF.
- D6 odeslání vzorků akcí u kufru i tlačítkem v tabletu, cenu účtuje PF.
