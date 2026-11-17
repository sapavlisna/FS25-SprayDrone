# Pneumatické nožky (Middle a Max) — návrh

Zadání (Pavel, 2026-10-13): stabilizační nožky se mají vysouvat jen když vlek nestojí rovně a je odpojený, pomaleji a plynuleji, se zvukem vzduchu
(sykot). K tomu malá vzduchová nádrž; nožky se mají vysunout spínačem u nádrže a pak se zase s sykotem pomalu zasunout. Když je málo vzduchu, zapne se elektrocentrála
a malý kompresor ho doplní. Platí jen pro Middle a Max. Mini se nemění (nožičky plošiny jako dnes).

## Co už je hotové (2026-10-13)

- **Kdy se vysouvají**: `<legs levelTolerance="2.5" maxTilt="15">`. Do 2,5° náklonu stojí vlek dost rovně a nohy zůstanou zasunuté; nad tolerancí se vlek
  vyrovnává a nohy vyjedou; nad 15° se nerozloží (reálnou mez dává dosah nohou, viz `docs/DRON.md`, „Kolik jde vyrovnat“). `SprayDroneLevel.updateFlat`, test `tmp/f/test_level.py`.
- Nohy dnes jedou podle času skládání vleku (`SprayDroneLevel.getDeploy`, `foldStart` 0,97 → `levelStart` 0,86), tedy při rozkládání vleku, a za 3 s se zvládne i vyrovnání.

## Co zbývá

1. **Pomalejší pohyb**: nohy se při vyrovnání pohybují 0,97 → 0,86 (zhruba 0,3 s z animace 3 s), proto rychle a trhaně. Řešení: oddělit pohyb nohou od animace
   `foldLadder`: vlastní časovač v `SprayDroneLevel` (`legsDeploy` 0..1, rychlost např. 0,15 m/s, plynulé rozjetí a doběh) a rozkládání vleku na něj počká
   (`getIsFoldAllowed`, jako dnes čeká dron na nohy).
2. **Vzduchová nádrž**: nový fill unit „vzduch“ (vlastní fillType `SDT_AIR` z `xml/fillTypes.xml`, bez ikony v seznamu nádrží), ~20 l, plný tlak 10 bar; jedno
   vysunutí a zasunutí stojí část nádrže podle zdvihu (vysunutí 25 %, zasunutí 10 %). Stav „tlak“ se synchronizuje po síti, ukládá do savegame.
3. **Spínač u nádrže**: aktivační uzel (`Activatable` jako truhla nabíječky), akce „Vysunout / Zasunout nožky“ s tlakem v hlášce. Rozložení vleku nožky vysune samo
   (jen když je vlek mimo toleranci), spínač slouží k ručnímu zasunutí, vysunutí a dofouknutí.
4. **Kompresor**: malý kompresor u centrály; běží, když je tlak pod 70 % a centrála jede (nafta, `generatorRunning`), pomalu dofukuje (~1 bar/10 s). Zvuk
   `brakeCompressorSmall` (vanilla), při dosažení plné nádrže `compressedAir` jednorázově. Bez centrály nelze doplnit, hráč dostane hlášku „Zapni centrálu“.
5. **Zvuky**: sykot při vysunutí (`attachAirBrake`) a při zasunutí (`detachAirBrake` / `hydraulicAirySmallOpen`), tichý cvak patky při dosednutí (`clackVar4`).
   Vše vanilla šablony, hlasitosti naladit ve hře.
6. **Model v Blenderu** (Middle a Max): malá svislá nádrž na vzduch (např. 20 l, válec s manometrem) u centrály nebo v rámu, spínač (kulový ventil s pákou) na její čelní straně,
   hadičky k nohám nejsou nutné (zjednodušení). Uzly `airTank`, `airSwitchNode`, kolize `colAirTank`. Úprava `build_trailer_middle.py` a `build_trailer_max.py`.
7. **Překlady**: `sdt_air_*` v `translation_cz.xml` a `translation_en.xml` (nápisy akcí, hlášky nedostatek vzduchu / vypněte centrálu).

## Otevřené otázky

- Má se při nízkém tlaku vlek odmítnout rozložit (nutno nejdřív dofouknout), nebo se nohy vysunou „na poslední vzduch“ a zasunutí čeká na kompresor? Návrh: rozložit jde vždy,
  nohy se vysunou, i když tlak klesne na nulu (bezpečné pro hru), zasunout jde jen s tlakem — jinak se čeká na centrálu.
- Kolik vzduchu stojí cyklus: kolik cyklů vydrží plná nádrž (návrh: 6 vysunutí).
- Synchronizace pro multiplayer: tlak jako dirty flag vozidla s tolerancí (`SprayDroneFields.shared`).

## Odhad

Lua: nový modul `SprayDroneAir.lua` (stav tlaku, kompresor, aktivace) ~250 řádků + úprava `SprayDroneLevel` (časovač nohou). Blender: nádrž + spínač + export (Middle, Max). Testy offline
(`tmp/f/test_level.py` rozšířit o časovač a tlak). Ve hře ověřit: plynulost pohybu, zvuky, dofouknutí z centrály, uložení tlaku.
