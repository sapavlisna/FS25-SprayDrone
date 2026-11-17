# Plán 0.8.0.0 — malý vlek s dronem

## Stav (2026-09-28, test T hotový společně s 0.9)

- **Otestováno ve hře** (6 běhů, slot 11, snímky `out/mod_build/t09_*`): opěrné kolečko, plynulé rozkládání a
  skládání, pořadí ukazatelů a řádek nabíječky (2–5 baterií), přesuny baterií, nabíjení všech najednou a nafta
  podle počtu, úchyty mizí, bodová světla jen nad 2 m (noc), kužely postřiku, heliport, nabíječka s kabelem,
  hadice (namotaná / ležící / prověšená k M a S), zaoblené přelety a půlkruhové přejezdy (log a mapa), plynulé
  stoupání a klesání (log), nastavení v plánovači (klik, kolečko, Q/E, uložení), překážky a odstup na poli 2,
  dosah 1500 m, odhady proti letu (−1 až +6 %), IBC a vypouštění dronu, uložení/načtení s pokračováním mise.
  Přepočet trasy 2–8 ms, na poli 2 při klikání bočního odstupu až 133 ms. V logu hry žádné chyby modu.
- **Opraveno při testu**: `Alt+1` / `Alt+2` (a neaktivní `Alt+8`, `Alt+0`) pouštěly vanilla osu tempomatu, když akce
  modu nešla — akce teď zůstávají aktivní a jen se skryjí (`updateActionEventStates`, `updateTransferActionEvents`).
- Neověřeno ve hře: pojistka s odstupem 1 m, herbicid po vyprázdnění vleku, hadice u L zblízka, MP.
- `DEBUG_FLIGHT` a `DEBUG_POWER` vráceny na `false`. Otevřené: strop dosahu 1500 m (z baterie vychází víc),
  neudělané z L1 (obejití překážky bokem uvnitř plochy, pojistka při svislém pohybu) — `docs/DRON.md` „Na příště“.
- Pavlovy poznámky z prvního přerušeného testu (nabíječka místo podložky, ukazatel nabíječky, nabíjení všech najednou,
  hadice z modrého navíječe) zapracovalo kolo oprav 2 (B2 + L3) a test je potvrdil. Kontrakt uzlů kola 2:

  | mapping | co |
  |---|---|
  | `batteryCharger` | krabice nabíječky v rohu horní paluby (místo smazaného navíječe B), sloty `batterySlotDeck1..5` jsou v ní |
  | `chargerCable` | statický volně prověšený kabel nabíječka → elektrocentrála (jen vizuál) |
  | `fillHoseCoil` | hadice namotaná na modrém navíječi (viditelná u složeného vleku) |
  | `fillHoseStart` | místo, kde hadice opouští modrý navíječ / vede k nádrži |
  | `fillHoseLay1..8` | body volně položené, zkroucené hadice na kraji horní desky (rozložený vlek, klid) |
  | `fillHoseSeg1..24` | články hadice: válec délky 1 m podél lokální +Z, počátek na začátku; skript je rozmístí po křivce |
  | `fillHoseNozzle`, `fillHoseParkPos`, `Drone_A_FillPort` | jako dřív; `fillHoseParkPos` = konec položené hadice na desce |

  Staré `fillHoseRoot` a `fillHoseSegment` zmizí.

Zdroj požadavků: `docs/DRON.md`, sekce „Na příště" (body 1–16). Cíl: všechno postavit ve třech souběžných
proudech **bez spouštění hry** a pak otestovat v co nejméně bězích hry (ideálně jednom).
Záloha stavu před 0.8: `blender/archiv/2026-09-28_pred_0.8/`.

## Proudy a vlastnictví souborů

| proud | kdo | body | smí měnit |
|---|---|---|---|
| **B** Blender | subagent B | 3, 5 (uzly), 11, 15 (model a sloty), 16 (model hadice) | `blender/*.py`, `.blend`, `blender/templates/*.xml.in` **mimo** element `<sprayDrone>…</sprayDrone>`, i3d a xml vozidla přes export |
| **L1** let | subagent L1 | 8, 9, 10, 12, 13 | `SprayDroneRoute.lua`, `gui/SprayDronePlannerScreen.*`, letová část `SprayDroneStation.lua`, eventy |
| **L2** vlek | subagent L2 | 1, 2, 4, 5 (logika), 6, 7, 14, 15 (logika), 16 (logika) | servisní část `SprayDroneStation.lua`, element `<sprayDrone>` v šabloně, nové konfigurace v šabloně, `tools/prepare_testsave.py` |
| **T** test | subagent T po B, L1, L2 | vše | cokoli; opravy chyb nalezených ve hře, `docs/DRON.md`, verze |

Sdílené soubory (`SprayDroneStation.lua`, `modDesc.xml`, překlady, šablona): **před každou úpravou úsek znovu přečíst**,
upravovat malými Edity, nic nepřeformátovávat, nepřesouvat cizí kód. Soubory jen přes Edit/Write (PowerShell rozbíjí
diakritiku). `sprayDroneTrailerCar.xml` ve vozidle je generovaný — měnit jen šablonu `.xml.in`.

Hra se v B, L1, L2 **nespouští**. Syntaxe Lua: `.venv\Scripts\python.exe tools\lua_check.py` (LuaJIT přes lupa) po
každé větší úpravě. Každý proud na konci zapíše předávací poznámku do `out/plan08/<B|L1|L2>.md`: co udělal, nové
parametry a uzly, co má T ve hře ověřit a jak (konkrétní kroky, klávesy, co v logu hledat), známá rizika.

## Kontrakt uzlů i3d (B vyrábí, L2 používá)

Všechny s `i3dMapping` stejného jména. L2 musí fungovat i bez nich (uzel chybí → vizuál se přeskočí, logika jede),
protože export B může doběhnout později.

| mapping | co | poznámka |
|---|---|---|
| `droneClamp1..4` | celý úchyt lyžiny (sloupek + čelist) | L2 skryje, když dron není složený |
| `battery1..5` | model baterie (vzor DJI DB1560, ~ 0,37 × 0,23 × 0,13 m, počátek uprostřed dole) | L2 je přesouvá mezi sloty |
| `batterySlotTransport1..5` | místa v držáku vedle centrály (dolní paluba) | při přepravě (vlek složený) |
| `batterySlotDeck1..5` | místa v rohu horní paluby | při rozloženém vleku |
| `batterySlotDrone` | místo baterie v dronu, pod `Drone_A_Tilt` | původní baterii modelu dronu B odstraní z geometrie |
| `fillHoseRoot` | základ hadice na horní palubě (navíječ / držák) | L2: viditelné jen rozložené |
| `fillHoseSegment` | válec hadice délky 1 m podél lokální +Z, počátek na začátku, dítě `fillHoseRoot` | L2 natočí a natáhne (`setScale` z) ke koncovce |
| `fillHoseNozzle` | koncovka, počátek ve špičce | L2 posouvá z `fillHoseParkPos` k `Drone_A_FillPort` |
| `fillHoseParkPos` | klidová poloha koncovky | |
| `Drone_A_FillPort` | plnicí hrdlo dronu, pod `Drone_A_Tilt` | |

## Rozhodnutí (platí pro všechny proudy)

- **Baterie (4, 15):** vlek nemá vlastní baterii. Baterií je celkem N = 1–5 (konfigurace v obchodě, výchozí 3, cena za
  kus), vlek má 5 slotů. Na složeném vleku jsou všechny baterie ve slotech u centrály a dron je bez baterie. Po
  rozložení se přesunou do rohu horní paluby a dron si vezme nejnabitější (≥ `readyLevel`, jinak čeká). Po přistání
  (výměna) dá svou do slotu a vezme **první plně nabitou** (nejvyšší náboj ≥ readyLevel). Před složením vleku jde
  baterie z dronu zpět do slotu. Centrála běží, když je zapnutá, je nafta a některá baterie ve slotu je pod 100 %
  (i složený vlek). N = 1 znamená: jedna baterie, nabíjí se jen ve slotu (dron čeká).
- **Dosah (13):** místo pevného `range` se poloměr počítá z energie plné baterie: let tam s plnou nádrží ve výšce
  přeletu (včetně stoupání), návrat s prázdnou, rezerva 30 s (jako dnes). Výsledek omezit rozumným stropem (např.
  1500 m) a zaokrouhlit. Kruh v mapě a ve světě se mění s nastavenou výškou přeletu. Pevný `range` z XML zůstává jako
  horní strop, jestli je nastaven.
- **Nastavení (9):** v plánovači (panel) výška přeletu nad překážkami (`obstacleClearance`, 2–20 m) a boční odstup
  od překážek (nový, 1–15 m, výchozí 4 m); ukládá se do vehicles.xml a jde eventem na server. Rovnou tam může být i
  `transitHeight` (minimální výška přeletu).
- **Odstup (10):** kontrola překážek počítá s poloměrem dronu (rotory ~1,5 m) + bočním odstupem. Když přímý přelet
  vede překážkou, trasa se buď zvedne nad ni, nebo (když je plocha) obejde. Překážky, které plánování našlo, se ukážou
  v mapě plánovače (značka + výška) a přelet v mapě odpovídá skutečné dráze.
- **Křivky (8, 12):** zaoblení rohů přeletů a přejezdů mezi řádky (oblouk s poloměrem podle rychlosti, řádek postřiku
  se nezkracuje — zaoblit jen mimo stříkanou část), plynulé stoupání a klesání za letu (profil místo „vystoupat na
  místě"). Kontrola překážek musí platit pro zaoblenou dráhu. Odhady času a energie musí zaoblení zohlednit.
- **Vyprazdňování (14):** akce ve vleku „Vypustit dron do vleku" (dron na plošině, stejný nebo prázdný druh v nádrži
  vleku) a „Přečerpat nádrž do IBC" (IBC/paleta s kapalinou do ~6 m, přijímá ten druh; rychlost 1–2 l/s, jde přerušit).
  Obě po síti eventem, server provede. Když je vlek i dron prázdný, přijme vlek jiný přípravek.
- **Ukazatele (2):** nahoře dron (nádrž, baterie v dronu), dole vlek (nádrž vleku, baterie ve slotech, nafta).
  Vanilla řádky vleku je potřeba přeřadit (přepsaná `getFillLevelInformation`).
- **Světla (6):** bodová světla LED vypnout, dokud dron sedí na vleku nebo je níž než ~2 m nad plošinou; LED samotné
  svítí dál.
- **Efekt (7):** postřik musí vypadat jako kužely pod tryskami, ne jako stěna do šířky 9 m. Záběr zůstává 9 m.
- **Rozložení (1):** dron se musí rozkládat plynule stejně jako skládat — najít, proč se rozloží naráz (čas skládání,
  `trailerFoldEnd`, směr animace), a opravit.
- **Úchyty (5):** úchyty viditelné jen se složeným dronem (fáze zavírání při skládání vidět být může), jinak skryté.

## Test (T)

1. Znovu export z Blenderu (šablonu mohly po exportu B změnit L1 a L2), `tools/lua_check.py`, `tools/validate_mod.py`.
2. `nvidia-smi` — když kartu drží cizí práce, nespouštět a říct to.
3. Připravit slot 11 (`prepare_testsave.py`, s IBC poblíž, s různě nabitými bateriemi), jedna hra, projít checklist ze
   všech `out/plan08/*.md`. Snímky jen okna hry. Hru ukončit bez uložení (kromě testu uložení).
4. Opravit, co ve hře selhalo, a další běh jen na to. Na konci `docs/DRON.md` (nové sekce, Stav 0.8.0.0, sekci
   „Na příště" vyprázdnit o hotové body), verze `0.8.0.0` v `modDesc.xml`, zpráva s výsledky a neověřenými věcmi.
