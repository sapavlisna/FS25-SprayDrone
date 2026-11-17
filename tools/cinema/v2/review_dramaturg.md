# Posudek dramaturga (fáze 2a): scénář v1

Posuzováno: `tools/cinema/v2/scenar.md` (verze 1) proti Pavlovu zadání v `prompts/00_meta.md`.
Technickou proveditelnost neřeším (to je role 2b). Měřítkem je zadání, ale bere se jako orientační.

## Souhrn

- Nálezy: **3 vysoké, 6 střední, 4 nízké**.
- Pokrytí zadání je jinak velmi dobré: všech osm beatů u všech tří vleků, látky (Max vápno, Mini herbicid, Middle hnojivo), pět detailů na vlek, výměna baterie i doplnění, produktová scéna, závěr se třemi vleky, žádné titulky.
- Izolace scén je ohlídaná systematicky (kódy Z1/Z2, vlastní „ve scéně“ a „NESMÍ“). Pohybová mapa je bez kolizí; švenky se nehromadí.
- Součty délek v kap. 6 jsem přepočítal a sedí.
- Tři nejdůležitější nálezy:
  1. **D-01:** Max se v jednom filmu stěhuje farma → rybník → farma. Chronologie 5m je navíc obrácená.
  2. **D-02:** Max beat 5 s naftou (O12) zamítám. Max má v beatu 5 plnit vápno přes mlýnek, a beat 5m je pak jeho „beat 5“.
  3. **D-03:** Švenk v `*-2.1` končí pohledem na západ, přímo do nízkého slunce. To odporuje Z8 i pravidlu v kap. 0.

---

## Nálezy

### Vysoká

**D-01 · max-3.x … max-8.x, kap. 4, O1/O3 · Max je na dvou místech a čas 5m je obrácený**
- Problém:
  - Max rozloží na dvoře (4.x), pak stojí rozložený u rybníka (5m), pak je zase na dvoře s drony (6.1, 7.x).
  - Pavel říká „Mini a Max k farmě/stodole“ a zároveň „sání je v rybníce“. Obojí dohromady jde jen tehdy, když je voda u farmy, nebo když se použije střih.
  - Scénář volí střih bez zdůvodnění a bez přechodu. Divák uvidí dvůr, les u vody a zase dvůr, ve všech případech s rozloženým vlekem.
  - Čas se nedrží. Ve filmu jde 5.1/5.2 (17:50) před 5m (17:45–17:50) a bezprostředně potom 6.1 (18:00). Světlo i čas skáčou zpět.
- Návrh:
  1. Do průzkumu O1 přidat jako první bod: je voda do ~22 m (sání 10 m + hadice 12 m) od rovného místa u stodoly, nebo kdekoli, odkud jde snadno dojet k farmě? Pokud ano, celý Max zůstane u farmy.
  2. Pokud ne, pořadí filmu bude 1, 2, 3, 4, **5m (= beat 5 Maxe)**, 6, 7, 8 s časy 17:40 → 17:45–17:50 → 18:00.
  3. 5m se pak natočí jako samostatná scéna s vlastním krátkým uvedením, například `max-5m.0` (5 s, příjezd nebo celek rybníka s Maxem). Pavel označuje scény jako místa, takže střih mezi nimi je přijatelný.
  4. Varianta „celý Max u rybníka“ (O3) je až záloha. Porušuje zadání „Max k farmě“ a ztrácí koridor „za budovami“ (6.4).

**D-02 · max-5.1, max-5.2, O12 · Nafta místo koncentrátu: zamítám**
- Problém:
  - Zadání říká „plnění koncentrátem“. Max má koncentrát vápno, které se plní přes mlýnek z big bagu (beat 5m).
  - Nafta do centrály není koncentrát a je čtvrtou látkou, kterou zadání nezná. Divák uvidí v beatu 5 „Mini nalévá herbicid, Middle hnojivo, Max naftu“, což je matoucí.
  - Tabulka látek v kap. 1 si odporuje: „vápno až v 5m“.
- Návrh:
  1. Smazat `max-5.1` a `max-5.2` (−12 s).
  2. Beat 5m prohlásit za Maxův beat 5, tedy „plnění koncentrátem Max“. ID klidně zůstane 5m, ale ve filmu je na místě beatu 5.
  3. Jednoduchý kanystr s naftou zůstává jen v produktové scéně.
  4. Pokud by Pavel chtěl kanystrový záběr pro paritu, stačí jediný záběr nafty u centrály ve 4.5 (detail centrál), ne samostatný beat.

**D-03 · mini-2.1, middle-2.1, max-2.1, kap. 0 a 2–4 · Švenk za sestavou míří do slunce**
- Problém:
  - SIL vede na západ (−x) a slunce je v 17:30 „nízko na západě“.
  - V 2.1 kamera stojí u silnice a sestava projede kolem a odjíždí na západ. Švenk za ní končí v ose silnice, tedy proti slunci.
  - To je přesně „slunce v objektivu“ (Z8), tedy protisvětlo, které scénář sám označil za „tmavé“ v dávce A. Je to v rozporu i s větou v kap. 0 „slunce vždy za kamerou nebo z boku, nikdy do objektivu“. Platí pro všechny tři filmy.
- Návrh:
  - Švenk ukončit v zadní třičtvrtě poloze (cca 60–70° od kolmice na silnici), dřív než se kamera stočí do osy. „Odjíždí“ pak řeší ODJ-efekt zmenšování a tele.
  - Nebo začít beat 1–2 dřív (17:00–17:10), kdy je slunce výš a mimo osu. Posun spadá do tolerance O13.
  - Nebo sluneční azimut ověřit v 2b a rozhodnout podle něj.

### Střední

**D-04 · max-5m.1 … 5m.4, O23 · Pumpa dostává víc času než celý vlek**
- Problém:
  - Pavel: „u pumpy a násypky méně“. Pumpa má 4 záběry za 16,5 s (5m.1–5m.4), kdežto pět detailů celého Maxe je 17,5 s.
  - 5m.4 je prázdný statický rám na 3 s, který nic nevypráví (slouží jen střihu na shodu).
  - Max celkem 192 s, ostatní filmy 141 s.
- Návrh:
  - Sloučit 5m.1 a 5m.2 do jednoho záběru (sací koš lze ukázat v ODJ/JIB-D na konci 5m.1), tedy −4 s.
  - 5m.3 zkrátit na 3 s a 5m.4 na 1,5 s.
  - S D-02 (−12 s) vychází Max na ~172 s, což je pro film s mlýnkem a dvěma drony přiměřené.
  - K O23 se vyjadřuji takto: vypustit `5m.2` (ano) a `6.1` (ano, pokud O20 nedopadne, viz D-12). **Nevypouštět `5m.8`** (závěrečná pointa „mlýnek běží, vápno jde do Maxu“) ani `7.4` (zadání chce „různé pohledy při práci“).

**D-05 · max-5m.1 · Chybí samotné „pumpa se připojí k vleku“**
- Problém:
  - Pavel: „pumpa se připojí k vleku, sání je v rybníce“. Scénář začíná hotovým stavem (hadice už jsou připojené).
  - U mlýnku se připojení ukazuje (5m.7), u pumpy ne. Je to nesymetrické a vypadá to, jako by pumpa byla k vleku „připojená od začátku“.
- Návrh:
  - V 5m.1 alespoň krátce ukázat koncovku výstupní hadice, jak se napojí na `waterHosePort3000` (nebo ji natočit jako samostatný detail 3 s).

**D-06 · mini-6.2, mini-6.3, middle-6.2, max-6.2, max-6.4 · Plánování ukazuje stavy, ne činnost**
- Problém:
  - Zadání je „plánování mise“. Scénář zakazuje v UI kurzor (Z5) a letovou plochu ukazuje už nakreslenou (6.4).
  - Divák uvidí hotovou mapu a kartu, ale ne to, že si misi sám vyklikal.
  - Pro Maxe je koridor ústřední věc zadání („u Maxe i s letovým koridorem“), takže vzniká jen výsledek.
- Návrh:
  - Pro 6.2 a 6.4 dovolit kurzor jako součást UI (není to HUD přes svět) a v 6.4 ukázat, jak plocha roste po bodech, alespoň 3–4 body.
  - Pokud to technika neumožní (O6), zapsat jako vědomou ztrátu a plochu ukázat aspoň „doplnit“ (zvýraznění po částech), ne jako hotový polygon od začátku.

**D-07 · middle-4.x, max-4.x · Chybí detail samotného dronu a mlýnku**
- Problém:
  - Pavel: „u všech věcí detailní pohledy na součástky“. Drone je detailně jen v Mini D1 (heliport). U Middle a Maxe se dron objeví až při letu a na desce (7.x).
  - Mlýnek (nejvýraznější nová věc Maxe) nemá žádný vlastní detail (motor, zelený prstenec, vstup, výstup, nádoba); 5m.7 a 5m.8 ukazují hlavně hadice.
- Návrh:
  - Doplnit krátký detail dronu na plošině (ramena, vrtule, trysky, kamera; 3 s) před vzletem, tedy na začátek beatu 7 u Middle a Maxe.
  - Do 5m.8 nebo před něj vložit 3 s detailu mlýnku. Mlýnek nemá detail jako vlek, ale má aspoň jeden.

**D-08 · max-5m.5 … 5m.8, O21 · Pořadí mlýnku proti zadání**
- Problém:
  - Zadání: „hadicí se připojí mlýnek, naplní se vápnem z big bagu a hadicí se propojí s Maxem“. To jsou dvě připojení hadicí kolem plnění.
  - Scénář má mlýnek stojící bez hadice, plnění a pak jedinou hadici do Maxu. První připojení (mlýnek k vleku nebo na místo pumpy) tam není.
- Návrh:
  - Ponechat pořadí 5m.5 → 5m.6 → 5m.7, ale v 5m.5 doplnit hadici od vleku k mlýnku (nebo ji v 5m.5 zvlášť ukázat). Jinak prohodit 5m.6 a 5m.7, jak naznačuje O21.
  - Rozhodnutí je nutné před fází 3 (záleží na tom, co hra vůbec umožňuje, viz posudek technika).

**D-09 · spol, kap. 0 a 7.1 · Čas a stav závěru nenavazují na beat 8**
- Problém:
  - Každý film končí v beatu 8 složením a odjezdem (18:30). Závěr `spol` je v 18:25 a vleky jsou rozložené a drony ve vzduchu. Po odjezdu se divák vrací o pět minut zpět.
  - Scénář neříká, kam se `spol` vkládá: na konec každého filmu, nebo jen na konec celého sestřihu.
- Návrh:
  - Zapsat v kap. 7.1, že `spol` je samostatný epilog mimo časovou osu filmů (jako `prod`), a říct, kde se používá.
  - Čas a světlo nechat (18:25), jen to nepopisovat jako návaznost.

### Nízká

**D-10 · mini-5.1, middle-5.1 · Štítky herbicidu i hnojiva jsou obojí zelené**
- Problém: v 5.1 jsou oba kanystry popsané jako „zelené štítky“. Látku pak divák pozná jen z textu na štítku, který se v PC záběru těžko přečte.
- Návrh: ověřit barvy štítků; pokud jsou shodné, v 5.1 držet záběr s čitelným štítkem aspoň 1 s (NAJ končí na štítku) nebo to výslovně popsat v kap. 1.

**D-11 · prod-2, prod-4 · Pohyb kamery vs. čitelnost**
- Problém: hlavička 7.2 říká „u každého předmětu se zastaví“, ale tabulka má plynulý TRK na 10 s pro 4 předměty. 2,5 s na předmět je na hraně čitelnosti.
- Návrh: v tabulce zapsat zastavení (min. 2 s statického rámu na každý štítek), případně prodloužit na 12 s a ubrat ze závěrečného celku.

**D-12 · O20 · Displej plánovače na vleku (x-6.1)**
- Problém: 6.1 stojí na neověřeném displeji. Beat 6 se po jeho vypuštění nezhroutí, ale ztratí vazbu „displej na vleku → mapa“.
- Návrh: pokud displej nesvítí, 6.1 vypustit a beat 6 začít přímo mapou. Žádný jiný záběr kvůli tomu měnit netřeba.

**D-13 · prod, O22 · Chybí záložní řešení pro drony a baterie**
- Problém: pokud dev mód neumí klonovat uzly, `prod-5` a `prod-6` nejdou a zadání chce „baterie a drony“.
- Návrh: záloha: drony i baterie z jednoho vleku odtrhnout jen jako předměty (bez vleku); pokud to nejde, `prod-6` nahradit záběrem dronů v letu z klidné scény, a to jen jako nouzovou variantu.

---

## Posouzení rozhodnutí scénáristy (kap. 10)

| ID | rozhodnutí | verdikt |
|---|---|---|
| O12 | Max beat 5 = nafta místo koncentrátu | **zamítnout** (D-02): Max beat 5 = vápno přes mlýnek (5m), nafta jen v prod |
| O23 | délka Maxe 192 s, návrh škrtů | **částečně přijmout** (D-04): škrtnout 5m.2 a podle O20 6.1; ponechat 5m.8 a 7.4; cíl ~172 s i s D-02 |
| O24 | mlýnek se nezapřahuje (c61 jen bonus; vlek zůstává stát) | **přijmout**: zadání o zapřažení nemluví a „připojí se hadicí“ stojí na stojícím mlýnku |
| O19 | tahač celou dobu zapřažený | **přijmout**: zadání (4–8 skládání a odjezd) předpokládá zapřaženou soupravu; odpojování by přidalo čas a rizika |
| O3 | Max na dvou místech (dvůr + rybník) | **neřešit až v průzkumu**, rozhodnout teď: viz D-01 (nejdřív hledat vodu u farmy, jinak přechod) |
| O18 | výklad „z druhé strany“ (beat 2) | **přijmout** jako výklad, ale opravit slunce (D-03) |
| O21 | pořadí mlýnek / big bag | viz D-08 |
| O1 | rybník | souhlasím, že rozhodnutí o případné náhradě patří dramaturgovi po průzkumu; kritérium: Middle musí ukázat vodu v záběru, Max musí mít sání ≤ 10 m od hladiny |
