# Revize 2026-10-04: sloučené nálezy Fáze 1 a plán Fáze 2

Zdroj: devět auditních reportů (G-car, G-mini, G-max, K, P, L1, L2, X, Z). Subagenti nesměli zapisovat `REPORT.md`, jejich
plné texty jsou jen v transkriptu session; podkladové skripty a data jsou v `out\revize\<role>\`. ID v závorkách odkazují na reporty.
Zadání a pravidla: `docs/REVIZE.md`. Čísla níže jsou z auditů (ověřeno skripty), nic z toho ještě není ve hře.

## 0. Rozhodnutí

Rozhodnuté Pavlem (viz konec dokumentu, doplní se): dolet, `usageScale`, těžké nádrže Car, zapřažení rozloženého vleku.
Ostatní beru podle doporučení auditů a Pavel je může vetovat: ceny dronů na Maxu ×2, ceny kanystrů ~240/260 €, kapacita koncentrátu 5 % nádrže,
čerpadlo plnění S 1 / M 1,5 / L 2,5 l/s, `palletRate` 20 l/s, skryté akce Alt+1/2 zviditelnit podle kontextu, názvy vleků přes `$l10n_`.

## 1. Kritické a vysoké

| ID | co | oprava | balík |
|---|---|---|---|
| X-01 | mlha postřiku hlásí `Particle System emitter mesh for shape 'mistM' could not be loaded`, mlha se asi nevykresluje; příčina neznámá | zkusit emitor jako vanilla (čtyřúhelník), atributy/TransformGroup, ověřit logem | g |
| L1-A1 | Max `activeDrones=1`: náhled dá dronu 2 celé pole, souhrn ×2 (potvrzeno lupa testem) | 2 řádky v `buildLegs` a `getRouteSummaryAll` | a |
| K-01 | rozložený vlek je KINEMATIC, ale rozložit jde i zapřažený → tahač se může zaseknout | viz rozhodnutí | f/a |
| K-02 | Mini: kanystry z bedny se objeví vpředu u oje, v centrále, ojí a rámu | `spawnSign` dozadu / do strany, ≥1,9 m | b+f |
| K-03 | zátěž na oji Mini 6,3 %, Max 18,1 % | těžiště Mini z=1,10, Max z=−2,31 | d, e |
| K-04/X-03/P-09 | brzda Max 3–5× slabší než vanilla | `force 0,5 maxForce 1,8–2,0 maxForceMass 26000` | f |
| K-05/X-04/P-03 | Car `maxMass` 2000 kg neunese nádrže 1500/3000/5000 l | viz rozhodnutí | f |
| GM-01 | Mini: po rozložení dron dosedne lyžinami do závěsu desky (48 mm) | konzola/pant/vložka `x ±0,35 → ±0,55` (4 místa, ověřeno v Blenderu) | d |
| GM-02 | Mini: klidová hadice leží v krytech předních nožiček | přetrasovat Lay4/Lay5, sloupky `0,55 → 0,65` | d |
| P-01 | dolet 1500 m pro všechny varianty | per varianta `maxRange` v blocích `<drone>` | f |
| P-02 | `usageScale 1` = 292 l/ha, 4,6× víc než čerpadlo DJI | viz rozhodnutí | f |
| X-05/GM-12 | Mini: oj 0,95 m, čelo se dotkne pneumatiky velkého traktoru při 32–41° (limit 50–70°) | oj ≥ 1,8 m (`COUPLER_Y`) | d |
| X-06 | Car/Mini nejdou za MF 8570 (jen háček `trailer`) | třetí `inputAttacherJoint` `trailer`, výška 0,90 | f |
| P-04 | Max nese dva drony za cenu jednoho | ceny dronů na Maxu ×2 | f |
| Z-01 | hučení centrály ~12,5× hlasitější než ve vanille (`generator05 volumeScale=5`) | `volumeScale="1"`, `outdoor` 0,5–1,0 | f |

## 2. Střední

- **L1-B2** (MP) čtyři události nekontrolují farmu hráče; `AreaEvent` bez ořezu bodů. · **L2-A1** `ToolboxEvent` COUNT_BITS 4 → 6 (Max až 24/33 kanystrů). · **L1-B6** pojistka stoupá bez stropu. · **L1-B5** spící vlek se nemusí probudit k nabíjení (test).
- **L1-B1/L2-A2/Z-13** `SprayDroneDebug.ENABLED=true` v ostré verzi, spam logu; vypnout a chránit `Logging.info` v `getHopHeight`/náhledu.
- **X-07** `rotor#fadeOut="300"` (sekundy ×1000) → `0.3` (10 výskytů). · **X-08** Alt+1/2/5/6 kolidují s EnhancedVehicle (ve save neaktivní).
- **K-06/X-09** `foliageBending` mírou Z zrcadleně u Mini/Max (`export_car_mod.py:424-425`). · **K-07** opěrné kolečko se zvedne jen o 0,2 m → ≥0,35.
- **GM-03** Mini hadice vstupuje do čela desky (Lay3 +0,10–0,12). · **GM-04** Mini sací hadice prochází rohovým sloupkem centrály.
- **GMX-01** Max klidová hadice A/B přes víko truhly. · **GMX-02/03** víko truhly Max do lemu `TopLip_L` (`CHEST_EDGE_X 0,985 → 0,945`). · **GMX-04** mezera pneumatika–blatník 35 mm při zdvihu 120 mm (`FENDER_R +0,10` nebo `suspTravel`).
- **G-CAR-01/02** Car: víko truhly nabíječky v `WorkLight` (52 mm) a `TopLip_Front` (25 mm). · **Z-02/03/04** zvuk: žádná animace, čerpadlo, hadice, bedna ani postřik nemají zvuk (vanilla vzorky). · **Z-05** konec mise jen v HUD pro hráče ve vleku → ingame notifikace.
- **P-05..P-08, P-14** čerpadlo per varianta, koncentrát, ceny kanystrů, `palletRate`, `fillTriggerVehicle`. · **Z-09** pracovní/brzdová světla (přestavba modelu; odloženo).
- **Z-10** obrázky obchodu ukazují největší nádrž. · **X-02** Mini `enterReferenceNode` už opraveno v HEAD, ověřit v logu.

## 3. Nízké (do balíků, až je čas)

G-CAR-03..07, GMX-05..08, GM-05..10/13, K-08..15, L1-B3,B4,B7..B13, L2-B1..B15, Z-06..08,11,12,14..20, X-10..18, P-10..17 (včetně `power#slots="3"` pro Mini: P-11 = L1-A2),
refactoring (L1-C1..C7, L2-C1..C7): vyřezat/vypnout ladění, rozdělit `onLoad` a `updateFlight`, smazat mrtvé konstanty, sjednotit konstanty fází baterie (`Route` × `Station`), `batteryReserve` do XML.

## 4. Pracovní balíky Fáze 2 (disjunktní soubory)

| balík | soubory | obsah |
|---|---|---|
| **a** Lua jádro | `Station`, `Drones`, `Fields`, `Service`, `Pad`, `Hotspot`, `Ladder`, `Sound`, `Debug`, `events/*` | L1-A1, B1, B2, B6, L2-A1 (event), K-01B?, Z-03/04/05/06/12, ladění vypnout, refactoring C |
| **b** Lua plánovač a bedna | `Route`, `gui/SprayDronePlannerScreen`, `Toolbox`, `Mixer` | K-02, K-12, L2-A3, B5, B6, B8, B9, C1 (debug z Toolboxu), Z-08, Z-17 |
| **c** model Car | `build_trailer_car.py`, `export_car_mod.py` | G-CAR-01..07, K-07, K-06 (společné), Z-10 |
| **d** model Mini | `build_trailer_mini.py`, `export_mini_mod.py`, `headless_mini.py` | GM-01..09, X-05, K-03, K-07 |
| **e** model Max | `build_trailer_max.py`, `export_max_mod.py`, `headless_max.py` | GMX-01..05, K-03, K-07 |
| **f** XML, šablony, překlady | `blender/templates/*.xml.in` + vygenerované XML, `modDesc.xml`, `translation_*.xml`, `objects/canister/*.xml` | P-01..P-08, X-04/06/07, K-04/05, K-01A, Z-01/02/07/18, X-14, překlep L2-A4 |
| **g** efekty a zvuk | `effects/sprayMist.i3d`, `build_spray_mist.py`, `sounds/` | X-01 (první), Z-15, Z-02 animace |

Pořadí: **g (X-01)** a **f** + **a** + **b** paralelně (Lua a XML nesdílí soubory; šablony vlastní jen f), modely **c, d, e** paralelně (každý svůj `.blend`, jediný sdílený je `build_drone.py` → vlastní c, Max a Mini ho nesmí měnit),
exporty (12 min) až po schválení náhledů. `export_car_mod.py` (K-06) vlastní c; d/e jen nahlásí.
Sdílené společné funkce (`build_drone.py`, `build_trailer_car.py` pro Mini a Max): změna v c vyžaduje po sobě rebuild Mini a Max (nezávislé výstupy se musí zkontrolovat).

## 5. Fáze 3: testy ve hře (doplnění matice z auditů)

Navíc k matici v `REVIZE.md`: Car+Mini za pickup2017, MT655, JD 3650, Kubota RTV, MF 8570 (po třetím jointu); Max za MF 8570, JD 3650, MT655; plný rejd a couvání; Max 2×5000 l brzdění z 40 km/h;
Mini kanystry (K-02) 6–18 ks; rozložení zapřaženého (K-01); `activeDrones=1` na Maxu (L1-A1); mlha bez `Particle System` v logu; log po spuštění Mini bez `Index not found`; noc 22:00.
`prepare_testsave.py`: přidat volbu tahače (`--tractor`), `--diesel` zkrátit na kapacitu (X-18), Car `fillUnit id=1` (X-18).
Upozornění: disk `V:` (zakázaný) mohl projít `find /` v roli L2 (L2 to sám přiznal; nic z něj nečetl). Další agenti: výslovně zakázat prohledávání kořene disku.

## 6. Rozhodnutí Pavla

Odpovědi z 2026-10-05:

- **Dolet:** S 600 / M 900 / L 1200 m (`maxRange` v blocích `<drone>`; Car, Max stejně; Mini nosí jen S).
- **`usageScale`:** 0,2 (≈58 l/ha) pro všechny vleky.
- **Car těžké nádrže:** nechat všechny, zvednout `maxMass` (≈6200 kg) a úměrně `maxForceMass`.
- **K-01 (zapřažený rozložený vlek):** nic neměnit. Rozložený vlek zůstává kinematický. Pokud je tahač připojený a vlek se rozloží, nejde ho odpojit, dokud není zase složený
  (vanilla `detachingMinLimit 0,98` to už dělá; hláška `sdt_warning_foldFirst`). Ve hře jen ověřit, že odpojení opravdu nejde a hláška se zobrazí.

## 7. Stav testování (přerušeno Pavlem 2026-10-05)

Hotovo: T1 (Car), T2 (Mini), T3 + T4a (Max), balíky a–i. Přerušeno: **T4b** (Car, Mini, bedna na kanystry), hra zavřená, `game.xml` vrácený.
Po pokynu pokračovat T4b od začátku (agent byl zastaven, jeho rozpracovaný stav se neukládal): 1 bedna Car/Mini zblízka (nové žebra, nápis „kanystry 20 l“, štítek 450 L u Mini),
2 obchod/dílna Car (obrázek 1000 l, 5000 l), 3 Mini svah + hláška padHose + kolečko/zátěž na oji + brzdění, 4 lety S a L na Car a S na Mini, 5 noc, 6 naftový stojan + mixér, 7 en nejde (Steam).
