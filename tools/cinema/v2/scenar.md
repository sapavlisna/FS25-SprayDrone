# Scénář: video SprayDrone v2 (verze 2, po posudcích a průzkumu lokací)

Zadání a omezení: `tools/cinema/v2/prompts/00_meta.md`, fáze: `prompts/01_scenarista.md`, `02_kontrola_scenare.md`.
Podklady: `tools/cinema/edit/master.json`, `tmp/trailer/davka_A.md`, `davka_B.md`, `davka_U.md`, `tools/cinema/v2/lokace.md`.
Posudky: `review_dramaturg.md`, `review_technik.md`; vypořádání: `review_vyporadani.md`.
Počty dronů a nádrží jsou ověřené v `mod/FS25_SprayDroneTrailer/vehicles/*/*.xml`.

Změny proti verzi 1 (stručně): lokace podle průzkumu (Middle poloostrov u velké vody, Max celý film u potoka u pole), celé natáčení ve dne 10:00–14:00, Max beat 5 = vápno (pumpa, mlýnek, big bag; nafta pryč), plánovač u Maxe ukazuje fialovou letovou plochu (ne přelety), přidány detail dronu (7.0) a mlýnku, `spol` je epilog, `prod` bez klonování dronů, Max zkrácen na ~170 s.

## 0. Hlavička

Jeden scénář, tři filmy (stejná osnova, osm beatů) + dva doplňkové celky. Žádné titulky, žádná grafika, žádný zvuk hry.
Divák vidí jen to, co je ve hře: nápisy na modelech (štítky kanystrů, VSTUP/VÝSTUP na pumpě, popisky nádrží) a obrazovky plánovače.

| film | vlek (tahač) | látka | drony | místo | čas natáčení | cílová délka |
|---|---|---|---|---|---|---|
| `mini` | Mini (JD 3650), nádrž 300 l | herbicid | 1 (S) | silnice, štěrková cesta, dvůr farmy u stodoly | 10:00–11:30 | ~141 s |
| `middle` | Middle (pickup), nádrž 1000 l | tekuté hnojivo | 1 (výchozí S; v obchodě S/M/L) | silnice, štěrková cesta, travnatý poloostrov u velké vody | 11:00–12:30 | ~145 s |
| `max` | Max (MT655), 2 × 3000 l | **vápno** | **2** (stejné velikosti) | silnice u pole, travnatý pás u potoka (celý film) | 12:00–13:45 | ~170 s |
| `spol` | všechny tři vedle sebe (epilog) | – | 1 + 1 + 2 | dvůr farmy | ~13:00 | ~25 s |
| `prod` | předměty v řadě (vleky jen v pozadí) | – | S, M, L na vlecích v pozadí | rovný beton | ~13:00 | ~57 s |

### Místa (z `lokace.md`)

| kód | popis | pro |
|---|---|---|
| SIL | asfaltka z ≈ −662 (x od +76 po −80), sklon ~6,4°, jízda na západ (−x); ověřeno `b02_road` | beaty 1–2 Mini a Middle |
| CESTA | štěrková cesta přes pole ke stodole a silům (`b03_gravel`) | beat 3 a odjezd Mini |
| DVŮR | štěrkový dvůr kolem (−690, 150), stodola jižně (−700, 190), pole 3/4/5 severně | Mini celý, `spol` |
| POLO | travnatá louka na poloostrově u velké vody, místo (−618, 457), voda na (−618, 470), rákos u břehu, stromy kolem, štěrkové cesty, dům na JV, pole na jihu; ~300 m od farmy | Middle celý (beaty 3–8) |
| POTOK | travnatý pás mezi potokem a polem, místo (673, −34), voda na (686, −34); silnice severně i jižně, v dálce farma a kopce | Max celý (beaty 1–8, silnice u pole pro 1–3) |
| BET | rovná betonová plocha pro `prod` (určí průzkum) | `prod` |

### Společný čas a počasí

Pavel chce točit ve dne, snímky nesmí být tmavé: celé natáčení 10:00–14:00, jasno (`setWeather SUN`, variace 1), bez mlhy, žádný soumrak ani noc. Každý film je jeden souvislý úsek; v každé scéně se nastaví `setTime lock=true`. Před akcí kontrolní snímek jasu.
Slunce je ve dne vysoko a převážně na jihu. **Pravidlo kamery:** slunce nikdy do objektivu (azimut slunce zjistit pro konkrétní čas a místo ve fázi 3 a kameru orientovat až potom); u jízdy po SIL (na západ) kamera z jižní strany nebo z čela, ne z osy proti slunci.

| beat | mini | middle | max | poznámka |
|---|---|---|---|---|
| 1, 2 | 10:00 | 11:00 | 12:00 | silnice (Max: silnice u pole s potokem) |
| 3 | 10:10 | 11:10 | 12:10 | příjezd a zaparkování |
| 4 | 10:20–10:25 | 11:20–11:25 | 12:20–12:25 | rozložení a detaily |
| 5 | 10:30 | 11:30 | 12:35–12:55 (beat 5m) | Max: pumpa, mlýnek, big bag |
| 6 | mapa (6.1 v 10:40) | mapa (6.1 v 11:40) | mapa (6.1 v 13:05) | plánovač je celoobrazovkový |
| 7 | 10:45–11:10 | 11:45–12:10 | 13:15–13:35 | práce dronu |
| 8 | 11:30 | 12:30 | 13:45 | složení a odjezd |
| `spol` | 13:00 | | | epilog mimo časovou osu filmů |
| `prod` | 13:00 | | | samostatný, mimo filmy |

### Pojmy kamery a zákazy

Pohyby: **STAT**, **NAJ**, **ODJ**, **PAN-L / PAN-R**, **TILT-U / TILT-D**, **ORB-CW / ORB-CCW** (po / proti směru hodin při pohledu shora), **TRK** (boční jízda souběžně, směr L→R nebo R→L v obraze), **JIB-U / JIB-D**, **FOL** (zezadu za pohybujícím se), **TOP** (svisle shora), **DRON** (kamera vázaná na dron), **MAPA+ / MAPA− / MAPA-R** (u UI: přiblížení, oddálení, posun mapy doprava).
Typy záběru: **C** celek, **PC** polocelek, **D** detail.

| kód | co v záběru nesmí být |
|---|---|
| Z1 | cizí vlek (jiný z trojice Mini/Middle/Max), jeho tahač a dron. Výjimka: `spol` a pozadí `prod-1`, `prod-6`, `prod-7` |
| Z2 | cizí předměty: pumpa, násypka, mlýnek, big bag, relé tyč, tablet, cisterna, kanystry a pytle, které nejsou v řádku „ve scéně“ |
| Z3 | jiná vozidla a provoz, zvířata, lidé; postava hráče mimo záběr |
| Z4 | kamera v překážce (keř, koruna, větev, zeď, terén do 1 m od objektivu), strom nebo keř zakrývající hlavní objekt |
| Z5 | HUD, kurzor, nápověda, bublina, ikony hotspotů, debug čáry (světové čáry `Alt+5`, fialová plocha ve světě), titulky, grafika |
| Z6 | chyba fyziky: zabořené kolo nebo levitace, náklon nad 6° (na SIL 9°), škubání animace, duplicitní snímky (pod ~55 fps) |
| Z7 | dron mimo plán: ve vzduchu před vzletem nebo po přistání, roztočená vrtule u složeného vleku, dron mimo záběr, když je akce na něm |
| Z8 | špatné světlo: slunce v objektivu, strana vleku ve stínu stromů, přepal, odlesk přes štítek, tmavý snímek |
| Z9 | patrná „neviditelná ruka“ u kanystru a big bagu: nesmí být vidět spodek a okolí předmětu zblízka, kde by levitoval bez opory |

Tahač zůstává zapřažen celý film (beat 3 jen zastaví, beat 8 odjede). Mlýnek u Maxe se nezapřahuje (stojí samostatně).

## 1. Společná tabulka beatů

| beat | záměr (co má divák pochopit) | nálada | orient. s | odchylky |
|---|---|---|---|---|
| 1 | Souprava jede po silnici z dálky: pojízdná základna přijíždí za prací | klid, očekávání | 8 | stejné; Max na silnici u pole s potokem |
| 2 | Pohled zblízka: je to velké a skutečné; kamera se otáčí za ní | síla, rytmus | 7 | stejné |
| 3 | Dojela na místo: Middle na poloostrov u vody, Mini na dvůr farmy, Max na pás u potoka | usazení | 13–14 | **místo** |
| 4 | Vlek se rozloží (celek), pak pět detailů součástek | řemeslo | 27 | **Mini** plošina s dronem v bedně (bez žebříku a plachet), **Middle a Max** žebřík, plachty, anténa; Max 2 drony, 2 navíječe, 2 centrály |
| 5 | Plnění koncentrátem | praktično | 12 (Max 36) | **Mini** kanystr herbicidu, **Middle** kanystr hnojiva. **Max** = vápno: pumpa (sání v potoce) se připojí k vleku a naplní vodu, pumpa zmizí, mlýnek se připojí hadicí, big bag ho naplní vápnem, hadicí teče vápno do Maxu. Ve filmu je `5m` na místě beatu 5 (ID zůstává `5m`) |
| 6 | Plánování mise na mapě | soustředění | 16 (Max 21) | Mini a Middle: jedno pole bez koridoru; Max: pole od vleku dál, **fialová letová plocha** |
| 7 | Detail dronu, vzlet, práce z různých pohledů, přílet, doplnění a výměna baterie | vrchol | 41 (Middle 44, Max 43) | Max dva drony; Middle pohled z dronu; mlha: herbicid bílomodrá, hnojivo žlutozelená, vápno bílá |
| 8 | Složení a odjezd | uzavření | 16 | stejné |
| `spol` | Tři vleky a čtyři drony pohromadě, **epilog mimo časovou osu** (viz 7.1) | triumf | 25 | jediné místo, kde smí být víc vleků |
| `prod` | Co všechno k módu patří, s čitelnými štítky | katalog | 57 | samostatná scéna |

### Herní fakta, o která se scénář opírá

- Mini: dron S, 300 l, 3 baterie ve výchozí konfiguraci, bedna s dronem (panely `padHinge*`, boční stěny, nožičky), dvě bedny na 4 kanystry, bez žebříku a plachet. Rozkládá se 12 s.
- Middle: nádrž 1000 l, 48 kanystrů ve skříni s roletou, žebřík na pravém boku, plachty, centrála, truhla nabíječek, mixér a nádobka. Rozkládá se `foldLadder` ~5 s, pak se skriptem rozloží dron. Vápnový vstup má, ve filmu se nepoužívá.
- Max: dvě válcové nádrže A a B s ventily `waterHosePort3000` / `3000B`, dva drony, dva navíječe v kapsách, dvě centrály, vápnová nádobka s kohoutem (`limeInletNode`, `limeValveLever`). Rozkládá se 5 s + drony. Nafta se v tomto filmu neukazuje.
- Pumpa: spojky VSTUP (modrá, přepínatelná nádrž / sací koš) a VÝSTUP (červená), sání 10 m, výstup hadicí 12 m na vodní ventil vleku, `whPond` hledá vodu do 8 m od pumpy.
- Mlýnek: vstup hrubého vápna do nádoby, motor (zelený prstenec `millStartRing`), výstup jemného vápna `millOutletPort` hadicí na vápnovou spojku Maxu (12 m, mlýnek raději do 8 m od spojky), kohout se otevře levým tlačítkem.
- Slabiny: kanystr a big bag nese neviditelná ruka, prach mlýnku, tok vápna a hladina v nádržích nejsou vidět. Mlha postřiku vidět je. Kurzor myši v záznamu OBS vidět není.

---

## 2. Film `mini`

Tahač JD 3650, nádrž 300 l, herbicid, 1 dron S. Zákazy Z1–Z9 platí podle sloupce.

| ID | obsah | místo · čas | ve scéně | NESMÍ | typ · pohyb kamery | s |
|---|---|---|---|---|---|---|
| mini-1.1 | Sestava Mini + JD 3650 se vynořuje na horizontu silnice a jede k nám, zvětšuje se. Dron složený v bedně | SIL · 10:00 | Mini složený, JD 3650, silnice, louky | Z1 Z2 Z3 Z4 Z5 Z6 Z8; žádný provoz | C · STAT, tele (fov 12–18), 1,2 m nad krajnicí, slunce za kamerou nebo z boku | 8 |
| mini-2.1 | Sestava projede těsně kolem kamery (~36 km/h), kamera se otáčí za ní a končí ve 3/4 zezadu (ne v ose silnice) | SIL · 10:00 | tentýž | Z1 Z2 Z3 Z4 Z5 Z6 Z8; auto celou dobu na silnici v záběru | PC→C · PAN po směru jízdy, kamera na jižní straně | 7 |
| mini-3.1 | Sestava jede po štěrkové cestě přes pole k farmě, v pozadí stodola a sila | CESTA · 10:10 | Mini složený, JD, cesta, budovy | Z1 Z2 Z3 Z4 Z5 Z6 Z8; plot nebo keř mezi kamerou a sestavou | PC · TRK L→R (~25 m od cesty) | 8 |
| mini-3.2 | Sestava vjede na dvůr, zabrzdí, stojí; klid, nikdo nevystupuje | DVŮR · 10:10 | Mini složený, JD, stodola | Z1 Z2 Z3 Z4 Z5 Z6 Z8; hráč, jiné stroje | PC · STAT, nízko (0,8 m) | 6 |
| mini-4.1 | Stisk X: boční stěny bedny se sklopí, panely se rozloží v plošinu, dron se rozloží a stojí na heliportu | DVŮR · 10:20 | Mini rozkládaný, JD | Z1 Z2 Z3 Z4 Z5 Z6 Z7 Z8 | C · ORB-CW od zadního rohu k boku (animace 12 s, užitých ~10) | 10 |
| mini-4.2 | **Detail 1: plošina s heliportem a dronem** (kap. 5, Mini D1) | DVŮR · 10:22 | rozložený Mini | Z1–Z8; vrtule stojí, hadice mimo heliport | D · NAJ od nízka k heliportu a lyžinám | 3,5 |
| mini-4.3 | **Detail 2: elektrocentrála** (Mini D2) | DVŮR · 10:22 | tentýž | Z1–Z8; výfuk nemusí kouřit | D · TILT-U od panelu k výfuku | 3,5 |
| mini-4.4 | **Detail 3: šachta baterií, otevřená** (Mini D3) | DVŮR · 10:24 | tentýž | Z1–Z8; žádný dron ve šachtě, kabel nezakrývá sloty | D · STAT | 3,5 |
| mini-4.5 | **Detail 4: nádrž 300 l, nádobka na koncentrát, mixér** (Mini D4) | DVŮR · 10:24 | tentýž | Z1–Z8; kanystr (ještě nebyl) | D · TRK L→R | 3,5 |
| mini-4.6 | **Detail 5: navíječ hadice s koncovkou** (Mini D5) | DVŮR · 10:25 | tentýž | Z1–Z8; hadice vytažená k dronu | D · ODJ od koncovky k celému navíječi | 3,5 |
| mini-5.1 | Víko pravé bedny se odklopí, čtyři kanystry herbicidu, jeden se zvedne; najetí končí na štítku (min. 1 s čitelný) | DVŮR · 10:30 | rozložený Mini, kanystry herbicid | Z1 Z2 (kromě kanystrů) Z3 Z4 Z5 Z6 Z8 Z9; kanystry hnojiva a nafty | PC→D · NAJ k bedně | 6 |
| mini-5.2 | Kanystr se naklopí nad hrdlem koncentrátové nádrže, koncentrát se vlévá | DVŮR · 10:32 | tentýž | Z1 Z2 Z3 Z4 Z5 Z6 Z8 Z9; spodek kanystru zblízka | D · PAN-R od kanystru k hrdlu | 6 |
| mini-6.1 | Displej plánovače na vleku svítí (rozsvítí se `screenWake`) | DVŮR · 10:40 | rozložený Mini | Z1–Z8 | D · STAT | 3 |
| mini-6.2 | Plánovač: mapa, kruh dosahu rádia, pole v dosahu zeleně; zvýraznění přeskočí na vedlejší pole u stodoly (pole 4), mapa se plynule přiblíží | UI (mapa) | plánovač, pole 4 | Z5 (kurzor, bubliny „Cizí pole“, dialogy); ikony cizích vleků; červené hlášky | UI · MAPA+ | 7 |
| mini-6.3 | Karta plánu pole: dávky, čas letu, plocha, přípravek herbicid, baterie, vítr; krátce přepnutí na stránku Let | UI | karta pole 4 | Z5; červená varování | UI · STAT | 6 |
| mini-7.1 | Stisk Alt+8: vrtule se roztočí (~2 s), dron vzlétne z heliportu | DVŮR · 10:45 | Mini s dronem S, JD | Z1 Z2 Z3 Z4 Z5 Z6 Z7 Z8; stromy v ose stoupání | C · JIB-U | 6 |
| mini-7.2 | Dron letí nad polem 4 a stříká herbicid (bílomodrá mlha), kamera zezadu | pole 4 · 10:50 | dron S, pole | Z1 Z2 Z3 Z4 Z5 Z6 Z8; vlek jen daleko | PC · FOL | 6 |
| mini-7.3 | Svisle shora: stopa postřiku po řádcích | pole 4 · 10:52 | dron, pole | Z1 Z2 Z3 Z4 Z5 Z6 Z8 | C · TOP | 5 |
| mini-7.4 | Boční pohled nízko přes řádky, dron přelétá kolmo | pole 4 · 10:55 | dron, pole | Z1 Z2 Z3 Z4 Z5 Z6 Z8; keře v popředí | PC · TRK R→L | 5 |
| mini-7.5 | Dron se vrací, klesá k vleku a přistává na heliport | DVŮR · 11:00 | dron, Mini, JD | Z1 Z2 Z3 Z4 Z5 Z6 Z8; dron mimo záběr v poslední sekundě | PC · STAT, tele | 7 |
| mini-7.6 | Dron na desce (baterie 20 %, nádrž prázdná): hadice se napojí, doplní se nádrž (20 l za 20 s), souběžně výměna baterie (5 s) | DVŮR · 11:05 | Mini, dron, hadice, baterie | Z1 Z2 Z3 Z4 Z5 Z6 Z8 | PC · ORB-CCW | 8 |
| mini-7.7 | Detail výměny: vybitá baterie z dronu do šachty, plně nabitá do dronu (stejný take jako 7.6) | DVŮR · 11:05 | dron, truhla | Z1–Z8 | D · NAJ | 4 |
| mini-8.1 | Stisk X: dron složí ramena a listy, bedna se zaklopí, víko šachty se zavře | DVŮR · 11:30 | Mini skládaný, JD | Z1 Z2 Z3 Z4 Z5 Z6 Z7 Z8 | C · JIB-D | 8 |
| mini-8.2 | Tahač rozjede sestavu, odjíždí po cestě pryč | CESTA · 11:30 | Mini složený, JD | Z1 Z2 Z3 Z4 Z5 Z6 Z8 | C · STAT, tele | 8 |

---

## 3. Film `middle`

Tahač pickup, nádrž 1000 l, tekuté hnojivo, 1 dron (výchozí S). Beaty 3–8 na travnatém poloostrově u velké vody (POLO). Navíc ke Z1–Z9 platí: v každé scéně na poloostrově nesmí být cizí vlek, mlýnek ani pumpa. Voda je v záběrech 3.2, 4.1, 7.5, 7.6 a 8.2 vidět v pozadí.

| ID | obsah | místo · čas | ve scéně | NESMÍ | typ · pohyb kamery | s |
|---|---|---|---|---|---|---|
| middle-1.1 | Pickup s vlekem Middle vyjíždí na horizont silnice a jede k nám | SIL · 11:00 | Middle složený (dron na střeše, plachty svinuté, žebřík složen), pickup | Z1 Z2 Z3 Z4 Z5 Z6 Z8 | C · STAT, tele | 8 |
| middle-2.1 | Projede kolem kamery, kamera se otáčí za ní do 3/4 zezadu, ukáže střechu s dronem a žebřík složený podél boku | SIL · 11:00 | tentýž | Z1 Z2 Z3 Z4 Z5 Z6 Z8 | PC→C · PAN po směru jízdy | 7 |
| middle-3.1 | Pickup jede po štěrkové cestě mezi stromy a loukami k poloostrovu | cesta k POLO · 11:10 | Middle složený, pickup | Z1 Z2 Z3 Z4 Z5 Z6 Z8; větve nesmí zakrýt vlek | PC · TRK R→L | 8 |
| middle-3.2 | Sestava zastaví na louce poloostrova, v pozadí hladina velké vody a rákos; kamera couvá a odhalí vodu | POLO · 11:15 | Middle, pickup, voda | Z1 Z2 Z3 Z4 Z5 Z6 Z8; hráč, zvěř, pumpa | PC→C · ODJ | 7 |
| middle-4.1 | Stisk X: plachty se rozvinou, žebřík se sklopí, vyjede stožár, dron se rozloží na horní plošině | POLO · 11:20 | Middle rozkládaný, pickup | Z1 Z2 Z3 Z4 Z5 Z6 Z7 Z8 | C · ORB-CCW | 10 |
| middle-4.2 | **Detail 1: žebřík** (Middle D1) | POLO · 11:22 | rozložený Middle | Z1–Z8 | D · TILT-U | 3,5 |
| middle-4.3 | **Detail 2: boční plachta na kolejnici** (Middle D2) | POLO · 11:22 | tentýž | Z1–Z8 | D · TRK L→R | 3,5 |
| middle-4.4 | **Detail 3: truhla nabíječek s plynovými vzpěrami** (Middle D3) | POLO · 11:24 | tentýž | Z1–Z8 | D · NAJ | 3,5 |
| middle-4.5 | **Detail 4: nádrž 1000 l, vodní ventil, nádobka a mixér** (Middle D4) | POLO · 11:24 | tentýž | Z1–Z8; hadice na ventilu | D · STAT | 3,5 |
| middle-4.6 | **Detail 5: stožár s anténou a GPS** (Middle D5) | POLO · 11:25 | tentýž | Z1–Z8; stožár stažený | D · JIB-U podél stožáru | 3,5 |
| middle-5.1 | Skříň na kanystry: roleta jede nahoru do pouzdra, police s kanystry hnojiva; najetí končí na štítku (min. 1 s) | POLO · 11:30 | rozložený Middle | Z1 Z2 (kromě kanystrů) Z3 Z4 Z5 Z6 Z8 Z9; kanystry herbicid a nafta | PC→D · NAJ | 6 |
| middle-5.2 | Kanystr nakloněný nad hrdlem koncentrátové nádrže, koncentrát se vlévá | POLO · 11:32 | tentýž | Z1 Z2 Z3 Z4 Z5 Z6 Z8 Z9 | D · STAT, nízko | 6 |
| middle-6.1 | Displej plánovače na vleku, najíždí kamera | POLO · 11:40 | rozložený Middle | Z1–Z8 | D · NAJ | 3 |
| middle-6.2 | Plánovač: mapa s kruhem dosahu, vybere se pole jižně od poloostrova (přímý přelet), mapa se plynule oddálí | UI | plánovač | Z5; ikony cizích vleků; „Cizí pole“ | UI · MAPA− | 7 |
| middle-6.3 | Karta plánu pole: dávky, čas letu, plocha, přípravek tekuté hnojivo, baterie | UI | karta | Z5 | UI · STAT | 6 |
| middle-7.0 | Detail dronu na plošině: ramena, vrtule, trysky, kamera | POLO · 11:45 | Middle, dron | Z1–Z8; dron se nesmí hýbat | D · NAJ | 3 |
| middle-7.1 | Alt+8: vrtule se roztočí, dron vzlétne z horní plošiny a míří nad pole | POLO · 11:46 | Middle, dron | Z1 Z2 Z3 Z4 Z5 Z6 Z7 Z8; větve nad vlekem | C · TILT-U | 6 |
| middle-7.2 | Dron letí nad polem a rozprašuje hnojivo (žlutozelená mlha), kamera za ním | pole jižně · 11:50 | dron, pole | Z1 Z2 Z3 Z4 Z5 Z6 Z8 | PC · FOL | 6 |
| middle-7.3 | Svisle shora: stopa postřiku po řádcích | pole jižně · 11:52 | dron, pole | Z1 Z2 Z3 Z4 Z5 Z6 Z8 | C · TOP | 5 |
| middle-7.4 | Pohled z palubní kamery dronu (kamera vázaná na dron, ne Alt+9): řádky pod ním; záloha boční TRK | pole jižně · 11:55 | dron, pole | Z5 (HUD hry); Z4 | C · DRON | 5 |
| middle-7.5 | Dron se vrací zprava doleva, klesá a přistává na horní plošinu | POLO · 12:00 | dron, Middle | Z1 Z2 Z3 Z4 Z5 Z6 Z8; dron mizí v zeleni | PC · PAN-L | 7 |
| middle-7.6 | Dron na desce: hadice, plnění, výměna baterie; v pozadí voda | POLO · 12:05 | Middle, dron, hadice | Z1 Z2 Z3 Z4 Z5 Z6 Z8 | PC · ORB-CW | 8 |
| middle-7.7 | Detail: baterie ze slotu dronu do truhly a nová zpět (stejný take) | POLO · 12:05 | dron, truhla | Z1–Z8 | D · STAT | 4 |
| middle-8.1 | Stisk X: dron se složí, žebřík se zvedne, plachty se svinou, víko truhly se zavře, stožár se zasune | POLO · 12:30 | Middle skládaný | Z1 Z2 Z3 Z4 Z5 Z6 Z7 Z8 | C · ODJ | 8 |
| middle-8.2 | Pickup odjíždí z poloostrova po štěrkové cestě | POLO→cesta · 12:30 | Middle složený, pickup | Z1 Z2 Z3 Z4 Z5 Z6 Z8 | C · TRK L→R | 8 |

---

## 4. Film `max`

Tahač MT655, 2 × 3000 l, vápno, **2 drony**. Celý film u potoka u pole (POTOK, bez stěhování). Max stojí na travnatém pásu podél potoka **levým bokem k vodě** (vodní ventily `waterHosePort3000` / `3000B` směřují k vodě, pumpa mezi vlekem a potokem). Navíc ke Z1–Z9: pumpa, mlýnek a big bag smí být jen v záběrech `5m`; v záběrech 6–8 už nejsou (pumpa zmizela, mlýnek a big bag se odstraní).

| ID | obsah | místo · čas | ve scéně | NESMÍ | typ · pohyb kamery | s |
|---|---|---|---|---|---|---|
| max-1.1 | Max s MT655 se vynořuje na horizontu silnice u pole, obrovský, dva drony složené nahoře | silnice u POTOKU · 12:00 | Max složený, MT655 | Z1 Z2 Z3 Z4 Z5 Z6 Z8 | C · STAT, tele | 8 |
| max-2.1 | Projede kolem kamery; kamera se otáčí za ním do 3/4 zezadu; ~10 m, tandemová náprava, mohutné nádrže | silnice u POTOKU · 12:00 | tentýž | Z1 Z2 Z3 Z4 Z5 Z6 Z8; sklon silnice nezvedá přední kola | PC→C · PAN po směru jízdy | 7 |
| max-3.1 | Max odbočí ze silnice a jede po trávě podél pole k potoku, v dálce farma a kopce | silnice → POTOK · 12:10 | Max složený, MT655, pole | Z1 Z2 Z3 Z4 Z5 Z6 Z8; keře u potoka mezi kamerou a sestavou | PC · TRK L→R | 7 |
| max-3.2 | Souprava zastaví na pásu u potoka, levý bok k vodě, zadní konec nejblíž kameře | POTOK · 12:10 | Max složený, MT655, potok | Z1 Z2 Z3 Z4 Z5 Z6 Z8; hráč, pumpa | PC · STAT, nízko | 6 |
| max-4.1 | Stisk X: plachty se rozvinou, žebřík se sklopí, vyjede stožár, oba drony se rozloží na dvou plochách | POTOK · 12:20 | Max rozkládaný, MT655 | Z1 Z2 Z3 Z4 Z5 Z6 Z7 Z8 | C · ORB-CW od zadního rohu k boku | 9 |
| max-4.2 | **Detail 1: žebřík s madly** (Max D1) | POTOK · 12:22 | rozložený Max | Z1–Z8 | D · TILT-U | 3,5 |
| max-4.3 | **Detail 2: plachty a kolejnice** (Max D2) | POTOK · 12:22 | tentýž | Z1–Z8 | D · TRK L→R | 3,5 |
| max-4.4 | **Detail 3: truhla nabíječek a dva navíječe v kapsách s víky** (Max D3) | POTOK · 12:24 | tentýž | Z1–Z8 | D · NAJ | 3,5 |
| max-4.5 | **Detail 4: dvě elektrocentrály s výfuky** (Max D4) | POTOK · 12:24 | tentýž | Z1–Z8 | D · STAT | 3,5 |
| max-4.6 | **Detail 5: vodní ventily nádrží A a B a vápnová spojka s kohoutem** (Max D5), tedy místa, kam se v beatu 5 napojí hadice | POTOK · 12:25 | tentýž | Z1 Z2 Z3 Z4 Z5 Z6 Z8; hadice na spojkách | D · ODJ od kohoutu | 3,5 |
| max-5m.1 | **Pumpa se připojí k vleku:** pumpa stojí na břehu, sací hadice (sací koš) leží v potoce, konec výstupní hadice se napojí na ventil nádrže A, motor naskočí a hadice se napnou | POTOK · 12:35 | Max rozložený, pumpa, hadice, potok | Z1 Z2 (kromě pumpy) Z3 Z4 Z5 Z6 Z8; hráč, mlýnek, big bag | C · TRK R→L podél břehu | 6 |
| max-5m.2 | Pumpa a sací koš pod hladinou, cedulky VSTUP (modrá) a VÝSTUP (červená): jen krátce (pumpa je vedlejší) | POTOK · 12:37 | pumpa, koš, hadice | Z1 Z2 (jen pumpa) Z3 Z4 Z5 Z6 Z8; odlesk slunce na hladině přes štítek | D · JIB-D k hladině | 3 |
| max-5m.3 | Pumpa v uzamčeném rámu, běží, výstupní hadice napnutá | POTOK · 12:38 | pumpa, ventil | Z1 Z2 (jen pumpa) Z3 Z4 Z5 Z6 Z8 | D · STAT (uzamčený rám) | 2,5 |
| max-5m.4 | Tentýž rám bez pumpy a bez hadic: pumpa „zmizela“ (střih na shodu), zůstane ventil a břeh. Stejný take, stejný čas, stejné světlo | POTOK · 12:38 | prázdné místo, ventil | Z1 Z2 (žádná pumpa, žádná hadice) Z3 Z4 Z5 Z6 Z8 | D · STAT (stejný rám) | 1,5 |
| max-5m.5 | **Mlýnek se připojí hadicí:** mlýnek stojí do 8 m od vápnové spojky, konec hadice od výstupu mlýnku se napojí na spojku (kohout zatím zavřený) | POTOK · 12:42 | Max, mlýnek, hadice | Z1 Z2 (kromě mlýnku, big bagu) Z3 Z4 Z5 Z6 Z8 | C→D · ORB-CCW | 7 |
| max-5m.6 | **Big bag naplní mlýnek vápnem:** big bag se zvedne nad nádobu mlýnku (vstup hrubého vápna), vyklopí se, vápno teče dovnitř | POTOK · 12:45 | mlýnek, big bag | Z1 Z2 Z3 Z4 Z5 Z6 Z8 Z9 | PC · TILT-D následuje klesající big bag | 7 |
| max-5m.7 | Detail mlýnku: nádoba, šnek, motor, zelený prstenec, výstup se spojkou; motor se spustí | POTOK · 12:48 | mlýnek | Z1 Z2 Z3 Z4 Z5 Z6 Z8 | D · NAJ | 3 |
| max-5m.8 | **Hadice propojí mlýnek s Maxem v chodu:** kohout se otevře, mlýnek mele (prstenec svítí), vápno jde hadicí do Maxu; celek obou | POTOK · 12:52 | Max, mlýnek, hadice | Z1 Z2 Z3 Z4 Z5 Z6 Z8; člověk | C · TRK L→R | 6 |
| max-6.1 | Displej plánovače na vleku svítí | POTOK · 13:05 | rozložený Max (bez pumpy a mlýnku) | Z1–Z8 | D · STAT | 3 |
| max-6.2 | Plánovač: mapa s kruhem dosahu a poli; zvýraznění přeskočí na vedlejší pole u potoka a pak na **vzdálenější pole** (strniště, v dosahu dronu), mapa se plynule přiblíží; v kartě pruh „Výška přeletu 20 m (kvůli překážkám)“, je-li pole za překážkami | UI | plánovač | Z5 (kurzor není v záznamu vidět, nesmí být bubliny „Cizí pole“); ikony cizích vleků; **žádné přelety a červené body překážek** (planner je nekreslí) | UI · MAPA+ | 6 |
| max-6.3 | Karta plánu: dávky, čas letu, plocha, přípravek vápno, baterie, 2 drony | UI | karta | Z5 | UI · STAT | 4 |
| max-6.4 | **Letová plocha (koridor):** fialová plocha se nakreslí od Maxe ke vzdálenějšímu poli, nejdřív 3 body (trojúhelník), pak přibývá bod a plocha se uzavře; mapa se pomalu posune; v kartě se změní údaje o přeletu | UI | plánovač s plochou | Z5; červená hláška „Vlek stojí mimo letovou plochu“; světové čáry `Alt+5` | UI · MAPA-R | 8 |
| max-7.0 | Detail jednoho dronu na plošině: ramena, vrtule, trysky, kamera | POTOK · 13:15 | Max, dron | Z1–Z8; dron se nehýbe | D · NAJ | 3 |
| max-7.1 | Alt+8: oba drony se roztočí a vzlétnou (druhý za ~3 s), míří ke vzdálenějšímu poli | POTOK · 13:16 | Max, 2 drony | Z1 Z2 Z3 Z4 Z5 Z6 Z7 Z8 | C · JIB-U | 7 |
| max-7.2 | Oba drony stříkají vápno vedle sebe na sousedních drahách (bílá mlha), kamera za nimi | vzdálené pole · 13:20 | 2 drony, strniště | Z1 Z2 Z3 Z4 Z5 Z6 Z8; vlek | PC · FOL | 6 |
| max-7.3 | Svisle shora: bílá stopa vápna na hnědém strništi, dvě dráhy | vzdálené pole · 13:22 | 2 drony | Z1 Z2 Z3 Z4 Z5 Z6 Z8 | C · TOP | 4 |
| max-7.4 | Boční pohled nízko přes strniště, drony přelétají | vzdálené pole · 13:25 | 2 drony | Z1 Z2 Z3 Z4 Z5 Z6 Z8; keře v popředí | PC · TRK R→L | 5 |
| max-7.5 | Oba drony se vracejí a po sobě přistávají (přední plocha první) | POTOK · 13:30 | Max, 2 drony | Z1 Z2 Z3 Z4 Z5 Z6 Z8 | PC · STAT, tele | 6 |
| max-7.6 | Jeden dron na desce: hadice, doplnění, výměna baterie (druhý čeká) | POTOK · 13:35 | Max, dron, hadice | Z1 Z2 Z3 Z4 Z5 Z6 Z8 | PC · ORB-CCW | 8 |
| max-7.7 | Detail: baterie z dronu do truhly a nová zpět, vedle truhla s 8 šachtami | POTOK · 13:35 | dron, truhla | Z1–Z8 | D · NAJ | 4 |
| max-8.1 | Stisk X: oba drony se složí, víka kapes navíječů se zaklopí, žebřík se zvedne, plachty se svinou | POTOK · 13:45 | Max skládaný | Z1 Z2 Z3 Z4 Z5 Z6 Z7 Z8 | C · JIB-D | 8 |
| max-8.2 | MT655 rozjede Max a odjíždí po trávě a silnici pryč od potoka | POTOK→silnice · 13:45 | Max složený, MT655 | Z1 Z2 Z3 Z4 Z5 Z6 Z8; mlýnek, pumpa | C · STAT, tele | 8 |

---

## 5. Pět detailů vleku (beat 4), konkrétně podle modelu

Každý detail ~3,5 s na rozloženém stojícím vleku (bez animací, jen pohyb kamery). Kamera se váže na uzel přes `#id` z `i3dMappings` (N11). Názvy uzlů jsou z i3d/xml ve `vehicles/`.

### Mini (bedna s dronem, bez žebříku a plachet)

| č. | detail | díly (názvy uzlů) | co je vidět | pohyb |
|---|---|---|---|---|
| D1 | plošina s heliportem a dronem | `padAnchor`, `padHingeZ` / `padHingeH` / `padHingeP`, `padSideL` / `padSideR`, `droneCarrier`, `Drone_S_Root` | rozložená plošina 1,86 × 3,04 m, heliport (kruh, mezikruží, H) na panelu H, lyžiny dronu na čarách H | NAJ nízko |
| D2 | elektrocentrála | `Gen_0_Body`, `Gen_0_Frame`, `Gen_0_Exhaust`, `Gen_0_ChargeSocket`, `Gen_0_Decals`, `generatorExhaust` | oranžová skříň v kleci, žaluzie, panel s klíčem a zásuvkou, tlumič s ohnutým výfukem | TILT-U |
| D3 | šachta baterií | `chargerLid` (otevřené ~100°), `batteryCharger`, `chargerCable`, `Chest_WallFront` / `Left` / `Rear` / `Right`, `Chest_Socket`, `battery1`–`battery3` | otevřená truhla se sloty, modré LED proužky, kabel | STAT |
| D4 | nádrž a míchání | `tankMain`, `Tank_Induction`, `Tank_Induction_Lid`, `Tank_Induction_Pipe`, `Tank_Induction_Fittings`, `Tank_Induction_Stand`, `Mixer`, `mixerMotor`, `Pump`, `Pump_Suction`, `Pump_Discharge`, `concentrateNeckNode` | popisek 300 L na nádrži, nádobka s víkem, kuželový mixér, čerpadlo | TRK L→R |
| D5 | navíječ hadice | `HoseReel_0_Drum`, `HoseReel_0_Axle`, `HoseReel_0_Flange+0.06` / `-0.06`, `HoseReel_0_Swivel`, `HoseReel_0_Base`, `HoseGuide_Post0` / `Post1` / `Top`, `fillHose`, `fillHoseCoil` | namotaná modrá hadice, vodítko, koncovka v držáku | ODJ |

### Middle

| č. | detail | díly (názvy uzlů) | co je vidět | pohyb |
|---|---|---|---|---|
| D1 | žebřík | `ladderHinge`, `ladderGrab`, `LadderHookBar`, `LadderHookPlate0` / `1`, `LadderHookTab0` / `1`, `LadderStop`, `Post_R0`–`Post_R2` | sklopený žebřík s příčkami na pravém boku, madla nad deskou | TILT-U |
| D2 | plachta | `tarpSideL`, `tarpSideLRoll`, `TarpTrack_L`, `TarpCorner_LF` / `LR`, `TarpCornerFoot_*`, `colTarpHingeL` | rozvinutá boční plachta na kolejnici, rohové patky | TRK L→R |
| D3 | truhla nabíječek | `chargerLid`, `chestStrutCylL` / `chestStrutCylR`, `batteryCharger`, `chargerCable` | otevřené víko držené vzpěrami, šachty s bateriemi | NAJ |
| D4 | nádrž a míchání | `tankMain1000`, `waterHosePort1000`, `Tank_Induction`, `limeInletNode` + `limeValveLever`, `Mixer`, `Pump`, `Pump_Suction`, `Pump_Discharge` | popisek NÁDRŽ 1000 L, ventil, nádobka, mixér | STAT |
| D5 | stožár s anténou a GPS | `antennaLarge` (`antennaLargeTele1` / `Tele2`, `antennaLargeCable`), `gpsRtkBox` (`gpsRtkBoxTele1` / `Tele2`), `antennaBase` | vysunutý teleskopický stožár s anténou a GPS RTK (zapnutí přes `nodeVis`) | JIB-U |

### Max

| č. | detail | díly (názvy uzlů) | co je vidět | pohyb |
|---|---|---|---|---|
| D1 | žebřík | `ladderHinge`, `ladderGrab`, `ladderArms`, `ladderUpper`, `LadderHolder_0Bar` / `1Bar`, `Post_L*` / `Post_R*` | sklopený žebřík před tandemem, madla | TILT-U |
| D2 | plachty | `tarpF`, `tarpL`, `tarpR` (+ `tarpFRoll`, `tarpLRoll`, `tarpRRoll`), `TarpRail_L` / `TarpRail_R`, `colTarpHingeF` | napnuté plachty na kolejnicích | TRK L→R |
| D3 | truhla nabíječek a navíječe | `chargerLid`, `chestStrutCylL` / `R`, `batteryCharger`, `HoseReel_Drum`, `HoseReel_BDrumB`, `ReelPocket_Floor`, `hoseLidHinge`, `hoseLidHingeB`, `fillHose`, `fillHoseB` | otevřená truhla s 8 šachtami, dva navíječe v kapsách, víka | NAJ |
| D4 | dvě centrály | `Gen_0_Body`, `generator2`, `generatorExhaust`, `generatorExhaust2`, `dieselNeckNode`, `dieselNeckNode2`, `chargerCable`, `chargerCable2` | dvě oranžové skříně, výfuky, hrdla nafty, kabely | STAT |
| D5 | vodní ventily a vápnová spojka | `tankMain3000` / `tankMain3000B`, `waterHosePort3000` / `waterHosePort3000B`, `inductionLime`, `limeInletNode`, `limeValveLever`, `Tank_Induction_Pipe`, `Mixer` | nádrže A a B, jejich ventily, bílá nádobka s kohoutem Storz | ODJ |

Mlýnek (`5m.7`, jediný detail): `Mill_Bin` (nádoba na hrubé vápno), `Mill_Auger` (šnek), `Mill_Body`, `Mill_Engine`, `millStartRing` (zelený prstenec), `millStartButton`, `millOutletPort`, `Mill_Hopper`.

---

## 6. Součty délek (užitečné sekundy kamery A)

| film | beaty 1–3 | beat 4 | beat 5 | beat 6 | beat 7 | beat 8 | celkem |
|---|---|---|---|---|---|---|---|
| `mini` | 29 | 27,5 | 12 | 16 | 41 | 16 | **~141 s** |
| `middle` | 30 | 27,5 | 12 | 16 | 44 | 16 | **~145 s** |
| `max` | 28 | 26,5 | 36 (5m) | 21 | 43 | 16 | **~170 s** |
| `spol` | | | | | | | **25 s** |
| `prod` | | | | | | | **57 s** |

Surové klipy se natočí delší; tabulky udávají cílovou délku použitého kusu.

---

## 7. Pomocné celky

### 7.1 `spol`: epilog, tři vleky vedle sebe (DVŮR · 13:00, jasno)

`spol` je **samostatný epilog mimo časovou osu filmů** (jako `prod`): nenavazuje na beat 8 žádného filmu. Používá se jednou na konci celého sestřihu (po všech třech filmech), případně jako samostatné video. Čas zůstává ve dne (13:00, žádná světla ani soumrak).
Ve scéně: Mini + JD 3650, Middle + pickup, Max + MT655, rozložené vedle sebe před stodolou (mezera ≥ 4 m), na zemi. Čtyři drony (Mini 1, Middle 1, Max 2) vzlétají a drží se nad vleky (`droneHover`). Jediná scéna, kde smí být víc než jeden vlek. Bez pumpy, mlýnku, big bagu.

| ID | obsah | NESMÍ | typ · pohyb | s |
|---|---|---|---|---|
| spol-1 | Z dálky ke třem vlekům před stodolou, drony vzlétají | Z2, Z3, Z4, Z5, Z6, Z8; dron mimo záběr dřív než vzlétne | C · NAJ | 9 |
| spol-2 | Pomalá boční jízda podél řady zepředu: Mini, Max, Middle | Z2, Z3, Z4, Z5, Z6, Z8; překrývání vleků | PC · TRK L→R | 8 |
| spol-3 | Kamera stoupá, tři vleky a drony ze shora, stodola a pole v pozadí | Z2, Z3, Z4 (koruna), Z5, Z6, Z8 | C · JIB-U | 8 |

### 7.2 `prod`: produktová scéna (BET · 13:00, jasno, samostatný den)

V jedné řadě na rovném betonu zleva doprava: kanystr hnojiva, kanystr herbicidu, kanystr nafty, pytel vápna 50 kg (`limeBag50`), big bag (`limeBigBag`), pumpa (`waterPump`), násypka (`limeHopper`), reléová tyč (`relayPole`, rozložená, zapnutá, zelený LED). Mezery ≥ 0,5 m.
**Drony a baterie (náhrada za klonování):** drony S, M, L stojí na **vlecích v pozadí řady** (Mini s dronem S, Middle s dronem M, Max s dronem L; typ dronu přes `setPadDrone`), baterie se ukážou **v truhle nabíječek** vleku v pozadí. Výjimka z Z1 platí jen pro `prod-1`, `prod-6`, `prod-7`; v `prod-2` až `prod-5` jsou vleky mimo záběr.
Kamera blízko (fov 25–35). **U každého štítku statický rám nejméně 2 s** (kanystry, pytel, pumpa, násypka), mezi nimi plynulý pohyb.
Zákazy: Z3, Z4, Z5, Z8 (štítek ve stínu kamery, odlesk), žádné cizí předměty (cisterna, traktor, balíky).

| ID | obsah | typ · pohyb | s |
|---|---|---|---|
| prod-1 | Celek řady z odstupu, vleky v pozadí | C · NAJ | 6 |
| prod-2 | Kanystry (hnojivo, herbicid, nafta) a pytel vápna: čtyři zastavení po ≥ 2 s, štítky čitelné | D · TRK L→R | 12 |
| prod-3 | Big bag zblízka, nápis a poutka | D · TILT-U | 5 |
| prod-4 | Pumpa (VSTUP, VÝSTUP) a násypka (VÁPNO, VÝSTUP), dvě zastavení po ≥ 2 s | D · TRK R→L | 9 |
| prod-5 | Reléová tyč: teleskopický stožár se zeleným LED | D · ORB-CW | 7 |
| prod-6 | Baterie v otevřené truhle nabíječek vleku v pozadí, LED proužky | D · NAJ | 5 |
| prod-7 | Tři vleky v pozadí s drony S, M, L (rozdíl velikostí) | PC · TRK L→R | 8 |
| prod-8 | Závěrečný celek řady | C · ODJ | 5 |

---

## 8. Pohybová mapa

Pravidlo: dva po sobě jdoucí záběry nesmí mít stejný typ pohybu ve stejném směru; švenky (PAN) stejným směrem nesmí jít po sobě; střídat najetí, odjetí, statiku, oblet, jeřáb. Výjimka: dvojice `max-5m.3` / `5m.4` (střih na shodu, schválená statika).

### Film `mini`

| # | ID | pohyb | směr | kolize |
|---|---|---|---|---|
| 1 | mini-1.1 | STAT | – | – |
| 2 | mini-2.1 | PAN | L | ne |
| 3 | mini-3.1 | TRK | L→R | ne |
| 4 | mini-3.2 | STAT | – | ne |
| 5 | mini-4.1 | ORB | CW | ne |
| 6 | mini-4.2 | NAJ | – | ne |
| 7 | mini-4.3 | TILT | U | ne |
| 8 | mini-4.4 | STAT | – | ne |
| 9 | mini-4.5 | TRK | L→R | ne |
| 10 | mini-4.6 | ODJ | – | ne |
| 11 | mini-5.1 | NAJ | – | ne |
| 12 | mini-5.2 | PAN | R | ne |
| 13 | mini-6.1 | STAT | – | ne |
| 14 | mini-6.2 | MAPA+ | – | ne |
| 15 | mini-6.3 | STAT | – | ne |
| 16 | mini-7.1 | JIB | U | ne |
| 17 | mini-7.2 | FOL | – | ne |
| 18 | mini-7.3 | TOP | – | ne |
| 19 | mini-7.4 | TRK | R→L | ne |
| 20 | mini-7.5 | STAT | – | ne |
| 21 | mini-7.6 | ORB | CCW | ne |
| 22 | mini-7.7 | NAJ | – | ne |
| 23 | mini-8.1 | JIB | D | ne |
| 24 | mini-8.2 | STAT | – | ne |

(2.1: směr PAN je „po směru jízdy“, tj. doleva při pohledu z jižní strany na jízdu na západ; 5.2 PAN-R je odděleno 21 záběry.)

### Film `middle`

| # | ID | pohyb | směr | kolize |
|---|---|---|---|---|
| 1 | middle-1.1 | STAT | – | – |
| 2 | middle-2.1 | PAN | L | ne |
| 3 | middle-3.1 | TRK | R→L | ne |
| 4 | middle-3.2 | ODJ | – | ne |
| 5 | middle-4.1 | ORB | CCW | ne |
| 6 | middle-4.2 | TILT | U | ne |
| 7 | middle-4.3 | TRK | L→R | ne |
| 8 | middle-4.4 | NAJ | – | ne |
| 9 | middle-4.5 | STAT | – | ne |
| 10 | middle-4.6 | JIB | U | ne |
| 11 | middle-5.1 | NAJ | – | ne |
| 12 | middle-5.2 | STAT | – | ne |
| 13 | middle-6.1 | NAJ | – | ne |
| 14 | middle-6.2 | MAPA− | – | ne |
| 15 | middle-6.3 | STAT | – | ne |
| 16 | middle-7.0 | NAJ | – | ne |
| 17 | middle-7.1 | TILT | U | ne |
| 18 | middle-7.2 | FOL | – | ne |
| 19 | middle-7.3 | TOP | – | ne |
| 20 | middle-7.4 | DRON | – | ne |
| 21 | middle-7.5 | PAN | L | ne |
| 22 | middle-7.6 | ORB | CW | ne |
| 23 | middle-7.7 | STAT | – | ne |
| 24 | middle-8.1 | ODJ | – | ne |
| 25 | middle-8.2 | TRK | L→R | ne |

### Film `max`

| # | ID | pohyb | směr | kolize |
|---|---|---|---|---|
| 1 | max-1.1 | STAT | – | – |
| 2 | max-2.1 | PAN | L | ne |
| 3 | max-3.1 | TRK | L→R | ne |
| 4 | max-3.2 | STAT | – | ne |
| 5 | max-4.1 | ORB | CW | ne |
| 6 | max-4.2 | TILT | U | ne |
| 7 | max-4.3 | TRK | L→R | ne |
| 8 | max-4.4 | NAJ | – | ne |
| 9 | max-4.5 | STAT | – | ne |
| 10 | max-4.6 | ODJ | – | ne |
| 11 | max-5m.1 | TRK | R→L | ne |
| 12 | max-5m.2 | JIB | D | ne |
| 13 | max-5m.3 | STAT | – | ne |
| 14 | max-5m.4 | STAT | – | **ano, záměrně** (střih na shodu s 5m.3) |
| 15 | max-5m.5 | ORB | CCW | ne |
| 16 | max-5m.6 | TILT | D | ne |
| 17 | max-5m.7 | NAJ | – | ne |
| 18 | max-5m.8 | TRK | L→R | ne |
| 19 | max-6.1 | STAT | – | ne |
| 20 | max-6.2 | MAPA+ | – | ne |
| 21 | max-6.3 | STAT | – | ne |
| 22 | max-6.4 | MAPA-R | R | ne |
| 23 | max-7.0 | NAJ | – | ne |
| 24 | max-7.1 | JIB | U | ne |
| 25 | max-7.2 | FOL | – | ne |
| 26 | max-7.3 | TOP | – | ne |
| 27 | max-7.4 | TRK | R→L | ne |
| 28 | max-7.5 | STAT | – | ne |
| 29 | max-7.6 | ORB | CCW | ne |
| 30 | max-7.7 | NAJ | – | ne |
| 31 | max-8.1 | JIB | D | ne |
| 32 | max-8.2 | STAT | – | ne |

### `spol` a `prod`

| # | ID | pohyb | směr | kolize |
|---|---|---|---|---|
| 1 | spol-1 | NAJ | – | – |
| 2 | spol-2 | TRK | L→R | ne |
| 3 | spol-3 | JIB | U | ne |
| 1 | prod-1 | NAJ | – | – |
| 2 | prod-2 | TRK | L→R | ne |
| 3 | prod-3 | TILT | U | ne |
| 4 | prod-4 | TRK | R→L | ne |
| 5 | prod-5 | ORB | CW | ne |
| 6 | prod-6 | NAJ | – | ne |
| 7 | prod-7 | TRK | L→R | ne |
| 8 | prod-8 | ODJ | – | ne |

Poznámky: PAN-L je v `middle` ve 2.1 a 7.5 (odděleno 18 záběry), v `mini` a `max` jen ve 2.1; PAN-R jen v `mini` 5.2. Žádný film nemá dva švenky po sobě. TRK L→R se opakuje (`mini` 3.1/4.5, `max` 3.1/4.3/5m.8), nikdy po sobě.

---

## 9. Kontrola pokrytí

| požadavek | kde |
|---|---|
| beaty 1–8 u všech tří vleků | kap. 2, 3, 4 (Max beat 5 = `5m`) |
| Max: pumpa se připojí, sání ve vodě, pumpa zmizí, mlýnek hadicí, big bag, hadice do Maxu | `max-5m.1`–`5m.8` |
| `spol`, `prod` | kap. 7 |
| každý záběr má seznam „nesmí“ | sloupec NESMÍ (Z1–Z9, kap. 0) |
| pět detailů vleku podle modelu | kap. 5 |
| pohybová mapa bez konfliktu | kap. 8 |
| celé natáčení ve dne 10:00–14:00, jasno | kap. 0 |
| žádné titulky ani grafika | Z5, jen obrazovky plánovače jako obsah hry |

---

## 10. Otevřené otázky pro technickou kontrolu (zbývající rizika)

- **O1 Místa.** Ověřit na místě: POLO (−618, 457) a POTOK (673, −34) mají rovinu pro soupravu a volné okolí pro kamery; sací koš pumpy musí být v ≤ 8 m od pumpy v hloubce ≥ 0,15 m (voda u POTOKU je na (686, −34), tj. 13 m od místa vleku, pumpa tedy ~6 m od vody); ventil Maxu směřuje k vodě. Beaty 1–3 Maxe: najít vhodný úsek silnice u pole s potokem a nájezd na pás.
- **O2 Pole.** Čísla polí (Mini pole 4; Middle pole jižně od poloostrova; Max vzdálenější pole od POTOKU) a dosah dronu (S 300 m, jinak anténa/relé). Strniště pro Maxe přes `setField growth=cut`. `selectField own=true` trvale mění vlastnictví polí.
- **O3 N6 (big bag do mlýnku).** Nad nádobu mlýnku se big bag s hrubým vápnem vyklopí sám jen předpokladem (ověřeno jen nad násypkou); záloha: 5m.6 přes násypku (`c62`). Mlýnek ≤ 8 m od vápnové spojky.
- **O4 Letová plocha (N2).** Plocha roste po bodech (3, 4, 5 bodů, tři nastavení): není ověřeno, že planner po každém nastavení překreslí hned; záloha: jen hotová plocha. Kurzor v záznamu není, takže „klikání“ se ukazuje jen zvýrazněním. Planner nekreslí přelety ani překážky.
- **O5 Middle na POLO.** Stromy kolem poloostrova: volný vertikální sloupec nad plošinou a v ose stoupání ≥ 25 m (pojistka dronu), přímý bezstromový přístup pro `driveTo mode=line` (3.1, 8.2), voda v pozadí v záběrech 3.2, 4.1, 7.5, 7.6.
- **O6 Dva drony Maxu vedle sebe (N3).** Souběžný vzlet není možný (odstup ~3 s), formace přes zbylé řádky (`coverLines`).
- **O7 `prod`.** Místo BET, `setPadDrone` variant M a L u Middle a Maxu, čitelnost štítků z fov 25–35, baterie viditelné v truhle vleku v pozadí.
- **O8 Slunce.** Azimut slunce v 10:00–14:00 zjistit pro každé místo a kameru orientovat podle toho (zejména 2.1 a TRK u vody); kontrolní snímek jasu před každou akcí.
- **O9 Izolace a úklid.** Mapa plánovače kreslí ikony všech vozidel: `isolate` (N1) nebo parkoviště mimo okno mapy; `dbg whPond/whOut/whConnect` se provedou na všech vozidlech s hadicí. Natáčení trvale mění slot 13 (vlastnictví polí, letové plochy, zaparkované soupravy), nikdy neukládat hru, na konci úklid.
- **O10 Anténa a GPS** (`middle-4.6`): `nodeVis` před `fold unfold`; ověřit, že se stožár vysune viditelně.
- **O11 Displej** (`x-6.1`): `screenWake` (N10); pokud nesvítí, 6.1 vypustit (−3 s).
- **O12 ID `5m`.** Pro kompatibilitu s `00_meta.md` a dalšími prompty zůstává ID `5m` (na místě beatu 5 u Maxe). Žádný beat 5 s kanystrem u Maxe už není.
- **O13 Pohled z dronu** (`middle-7.4`): `camPath at="middle:drone1" full=1`, osu dopředu uzlu ověřit; záloha boční TRK.
- **O14 Hladiny, prach, tok vápna** nejsou vidět; 5m.6–5m.8 spoléhají na big bag, prstenec, motor a hadici. Neviditelná ruka (Z9): kamera nad nebo ≥ 1,5 m od spodku předmětu.
- **O15 Mini a Middle: kanystr a štítek.** Barva štítku herbicid / hnojivo může být podobná (zelená), proto 5.1 končí najetím na čitelný štítek; mlha rozliší látku až při postřiku.
