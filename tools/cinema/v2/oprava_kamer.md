# Oprava kamer podle kontroly klipů (Mini, Middle)

Zdroj: `clips_qc.json`. Změněno v `tmp/v2/gen_mini.py`, `gen_middle.py`, `gen_common.py` (parametr `radius` u `isolate`/`drive_head`/`stationary_head`), scény přegenerovány (`gen_main.py`), `mk_take.py --dry` = 0 chyb.
Akce ve světě se nezměnily (stejné časování pro všechny kamery), mění se jen kamery a `isolate radius` (150 → 400 u akcí s cizími stroji v záběru; `vehicles=true` přesouvá jen odpojená vozidla, zapřažené stroje u stodoly zůstanou, proto jsou i kamery otočeny jinam).
Všechny nové polohy jsou neověřené: **ověřit snímkem** před natáčením. Souřadnice jsou lokální vůči vleku (`at`), kde není psáno jinak; +x = vlevo, −x = vpravo (pravý bok = jih u POLO i dvora).

## PŘETOČIT (jen uvedené kamery)

Mini: cesta A B C D · dvur-prijezd A B C · rozlozeni D · detaily B · kanystr A B C D · planovac A B (jen kvůli opravě koncentrátu v akci, kamery beze změny) · let B C · navrat-servis B C D · slozeni-odjezd A B
Middle: silnice B · cesta A B C · polo-prijezd A B C D · rozlozeni A B C D · detaily B · kanystr A B · let A B C · navrat-servis A C D · slozeni-odjezd A B C
Nepřetáčet: Mini silnice A/D a Middle silnice A/D už byly opraveny dřív (přetočit podle dřívější opravy); Middle planovac neřešeno (řeší hlavní agent); Middle silnice C (záloha, nejednoznačná oprava) a Mini let A, navrat-servis A, slozeni-odjezd C (stav ok) beze změny.

## Mini

- mini-cesta:A – konec trajektorie už nezajíždí do sorga (o1 28 → 24 m, o2 25 → 20 m, y ≥ 1,7); použít jen 0,5–7 s; isolate radius 400. Cizí tahač se sklápěčem na dvoře u stodoly může být v prvních sekundách ještě vidět (zapřažené stroje).
- mini-cesta:B – start o 5 m dál od plotu a výš (31 → 29 m vpravo, y 1,6–1,8), fov 36 → 33. Čas (protisvětlo) je společný pro akci, neměněn.
- mini-cesta:C – o 6 m na západ od stěny stodoly a dál od osy cesty (−751; 1,4; 164), fov 22 → 30, použít do 9 s.
- mini-cesta:D – beze změny kamery, isolate radius 400 (červený manipulátor ve stodole).
- mini-dvur-prijezd:A – y 0,8 → 1,7 nad zábradlí, (−666; 145); ikony hotspotů vypnout ve hře (`markers_off.lua`).
- mini-dvur-prijezd:B – sleduje soupravu (`tat=jd3650`) od 0 s, fov 30 → 26 (dřív prázdný dvůr 7 s a malá souprava).
- mini-dvur-prijezd:C – o 15 m na sever na štěrk (−640; 1,8; 137); isolate radius 400.
- mini-rozlozeni:D – chyba v kameře: chybělo `tat=M` (cíl byl světový bod, kamera mířila na pastvinu); opraveno. (Kamera C má stejný zápis, ale prošla – ponechána.)
- mini-detaily:B – 4.3 tilt začíná u centrály (cíl y 1,6 místo 2,0, kamera vpravo vpředu (−1,8; 1,5; 4,6)); 4.4 o 0,3 m výš.
- mini-kanystr:A – 5.1 shora do otevřené bedny na kanystr ve slotu 1 (−3,0; 1,9; −1,8 → −1,8; 2,0; −0,4, fov 36 → 28); 5.2 z výšky 2,5–2,7 m na kanystr nad hrdlem (spodek skrytý).
- mini-kanystr:B – fov 40 → 28, cíl mezi bednou a hrdlem (−0,65; 1,6; 1,8), y 2,6 (štítek čitelný).
- mini-kanystr:C – jen 5.2; o 1 m dál a výš (−2,5; 1,2; 4,0), cíl výš (y 2,0).
- mini-kanystr:D – 5.1 šikmo shora těsně do bedny (−2,2; 1,55; 0,9 → −1,9; 1,7; 0,5; fov 28 → 26) místo loga; 5.2 beze změny.
- mini-planovac:A,B – kamery beze změny; koncentrát se plní podle vleku už v gen_common, proto přetočit.
- mini-let:B – 7.3 z 95 m na 45 m nad polem, fov 32, cíl sleduje dron (`tat=mini:drone1`); isolate radius 400 (platí pro celou akci).
- mini-let:C – 7.2 zepředu blíž do osy letu (ox 4,5 → 1,5), fov 34 → 40.
- mini-navrat-servis:B – 7.7 míří na dron na heliportu (`tat=DR`) zleva zepředu, 3,3 m od dronu, y 1,5–1,6, fov 32 → 28 (dřív na šachtu, dron mimo záběr).
- mini-navrat-servis:C – 7.6 místo orbitu pohled těsně na truhlu s bateriemi (šachta x +0,5…+0,72, z 1,57) zleva zepředu, (2,8; 1,6; 3,6 → 2,2; 1,4; 2,8), fov 30 → 26.
- mini-navrat-servis:D – 7.7 odsun o 0,5 m a cíl o 0,25 m výš (vejde se baterie nad dronem), od 5,5 s přejezd na navíječ s hadicí (doplnění nádrže); klíče mixují vztažné soustavy dron → vlek (mod to vyhodnocuje po klíčích).
- mini-slozeni-odjezd:A – 8.2 sleduje soupravu (`tat=JD`), fov 20 → 14, tahač není ořezaný.
- mini-slozeni-odjezd:B – 8.2 o 7 m jižněji na štěrkovou cestu (z = 172, bez ohrady), fov 20 → 16, sleduje soupravu. Náklon při zatáčení (Z6) je chyba akce, neřešeno.

## Middle

- middle-silnice:B – (jen Middle, sdílená funkce `sil_action`) o 7 m blíž k silnici (z −655,5), y 1,7, fov 34/40/36, použít do 7 s. Mini a Max beze změny.
- middle-cesta:A – cíl o 1,5 m dopředu (lz −2 → −0,5), fov 34 → 38 (pickup se neřeže vpravo).
- middle-cesta:B – severní strana vedla keři (kamera v listí) → z jihu, 17 m od jízdy, y 3,0–3,2, s předstihem, fov 32 → 30. Sorgo od ≈ 25 m od cesty, proto ne dál.
- middle-cesta:C – na jižní straně cesty (−735; 1,5; 184), fov 22 → 30; isolate radius 400 (kombajn v přístřešku).
- middle-polo-prijezd:A – o 6 m na západ, y 3,8 → 4,8 (dřív 6 → 8), (−641; 3,8; 431), použít do 13 s.
- middle-polo-prijezd:B – z hladiny na břeh (−642; 2,6; 446,5), cíl (−620; 1,8; 456), fov 32.
- middle-polo-prijezd:C – z rákosu (−605; 1,4; 462) na (−610; 2,0; 449), cíl (−640; 1,8; 455).
- middle-polo-prijezd:D – poloha ověřená (−660; 5; 445) beze změny, fov 36 → 26 (pomalý nájezd).
- middle-rozlozeni:A – oblet nad rákosem: y 3,2 → 3,6 m, r 8,5 → 8, ly 1,8, fov 40 → 38 (stále pravý bok).
- middle-rozlozeni:B – oblet končí u středu levého boku (oz −2 místo 3), keř u pickupu už nevstoupí do záběru.
- middle-rozlozeni:C – z osy za vlekem na pravý bok (−10; 3,4; −4), cíl střed vleku, fov 36 (plachty, žebřík).
- middle-rozlozeni:D – jízda 9 m od osy ve výšce 2,8 → 4,0 m (nad rákosem ≈ 2 m).
- middle-detaily:B – 4.3 začíná až za pickupem (oz 0,2 → −2,4, keř v korbě mimo záběr); 4.4 (2,9; 4,1; 3,5), o 0,5 m výš.
- middle-kanystr:A – 5.1 nájezd těsně ke štítku kanystru ve slotu 1 (−2,6; 1,0; −5,6 → −1,1; 0,95; −3,7; fov 38 → 26); 5.2 z výšky 2,3–2,6 m, spodek skrytý.
- middle-kanystr:B – 5.1 pomalý nájezd na štítek (fov 34 → 26, cíl na kanystr); 5.2 y 2,4, fov 30.
- middle-let:A – 7.1 na severní straně (8,5; 2,6; −8,0) místo rákosu jižně od vleku.
- middle-let:B – 7.3 statika 45 m nad polem s cílem na dronu; 7.4 palubní kamera nahrazena FOL nízko zezadu (záloha TRK).
- middle-let:C – 7.0 o 0,5 m vpravo (mimo víko truhly); 7.2 ox 4,5 → 2,0, oy 2 → 4 m, fov 38.
- middle-navrat-servis:A – 7.6 orbit y 2,4/2,0 → 1,6/1,5, cíl níž (ly 0,2) na truhlu s hadicí; keř za pickupem zůstává.
- middle-navrat-servis:C – orbit r 5 → 4,2, y 1,6 → 1,8, ly 0,2; keř u pickupu zůstává.
- middle-navrat-servis:D – 7.7 kamera o 0,4 m doleva ((−1,4; 0,6; −1,8) → (−2,9; 1,0; −3,3)).
- middle-slozeni-odjezd:A – 8.1 odjezd kamery na sever (6; 2,8; −5 → 11; 3,4; −12) místo rákosu; 8.2 z 18 m, y 3,2.
- middle-slozeni-odjezd:B – 8.2 kamera ze stromu a keře na (−663; 3,2; 450) a na osu odjezdu, fov 26 → 20; 8.1 beze změny.
- middle-slozeni-odjezd:C – 8.1 oblet po levém boku (r 10 m, y 2,6 → 3,0) bez rákosu; 8.2 FOL z boku a výš (6; 4,5; −14).

## Poznámky

- Keř v korbě pickupu (nelze), cizí zapřažené stroje u stodoly a ikony hotspotů (Z5) kamerami nelze zcela vyloučit.
- `gen_main.py` hlásí `max-3.1` bez pokrytí (starší stav, mimo rozsah této opravy).
