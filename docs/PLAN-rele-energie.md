# Plán: relé s baterií, energie vleku, mapa, obchod, postřik (2026-10-15)

Zadání: 13 bodů od Pavla (relé tyč, kabeláž, nabíječka, obchod, hnojení/herbicid, mapa). Logo, polepy a nálepky jsou další kolo.
Fakta ověřená v kódu a ve zdrojácích hry (`tmp/gamesrc`); čísla řádků k 973b8e3.

## Zjištění, která mění zadání

- **Kruh relé (bod 1):** kreslí se jen v plánovači (`SprayDronePlannerScreen.lua:606-615`) a jen u *aktivního* relé
  (rozložené **a zapnuté** LMB, vzpřímené, nikdo ho nedrží, ≤ dosah vleku). Zapnutí přes LMB není nikde vidět → nejspíš
  proto „nekreslí“. Ve světě (Alt+5) se kreslí jen kruh vleku (`SprayDroneStation.lua:4016`), na mapě tyč nemá ikonu
  (`relayPole.xml:36` `mapHotspot available="false"`, a `Pallet` hotspot stejně skrývá).
- **Za letu se signál nekontroluje** – dosah se uplatní jen při plánování dávky (`buildLegs`, ořez kruhem). Když relé zmizí,
  rozlétaná dávka doletí. Bod 5 je tedy nová logika, ne oprava.
- **Prodej vleku:** drony jsou uzly vleku, `onDelete` → `deleteDrone` je smaže s ním (`Station:1222-1250`). Ověřit jen ve hře.
- **Míchání a plnění dronu dnes energii nepotřebuje** (`pumpDrone` `Station:2444`), jiný zdroj elektřiny než centrála v modu není.
- **Obchod (bod 10):** vlastní *záložku* mod nepřidá; vlastní *kategorie* jde jen do existující záložky (typ MISC/OBJECTS…),
  ruční nástroj (tablet) musí do kategorie typu HANDTOOLS. Celé „vše od SprayDrone na jednom místě“ umí vanilla **store pack**
  (`<storePacks>` v modDesc + `<storePacks>` ve storeData; dlaždice jako u DLC balíčků) – funguje pro vozidla i ruční nástroje.
- **Precision Farming (bod 11):** PF je interní mod hry. Dron zapisuje přímo `FSDensityMapUtil.updateSprayArea`, PF ale
  dusík/pH počítá ve `ExtendedSprayer:processSprayerArea` (hook na vanilla Sprayer) → **s PF hnojení dronem dusík v PF mapě
  nejspíš nezvedne** a PF statistiky ho nezapočítají. Herbicid PF hookuje přímo (`ExtendedWeedControl`), ale bere globální
  příznak spot-spray z posledního stroje (neviditelné fáze 1–2 pak dron nezničí).
- **Herbicid (bod 12):** vanilla herbicid ničí plevel ve všech fázích 1–6 (`maps_weed.xml:46-54`); na plodině ve fázi sklizně
  nic neudělá (mod takovou plodinu při plánu přeskakuje). Hustotu plevele mod nečte vůbec.

## Rozhodnutí (výchozí volby – Pavel může změnit)

| bod | volba |
|---|---|
| 2 baterie tyče | kapacita = **5 h provozu** (reálný čas × zrychlení hry jako nafta), plné nabití **20 min**; nabíjí se jen uložená na vleku při běžící centrále, nebo položená do 3 m od nabíjecí stanice (vanilla `ELECTRICCHARGE` plnicí místo, např. nabíječka na farmě) |
| 3 uložení na vlek | stejný princip jako kanystry v bedně: R u držáku → tyč (složená) zmizí do slotu, slot si drží baterii a sílu, na vleku je vidět model; R → vyndá. Vanilla `HandToolHolder` nejde – chce ruční nástroj, tyč je vozidlo |
| 4 nastoupení | tyč dostane `enterable` (E jen v rozloženém stavu), kamera kolem tyče, vpravo dole řádek baterie (`fillUnit` ELECTRICCHARGE), **B** (IMPLEMENT_EXTRA) zapne/vypne. Zapnutí na LMB zmizí |
| 5 signál | (a) rozloženou tyč nejde zvednout; (b) nejde ji složit/vypnout/vystoupit-a-vypnout, když je v jejím kruhu (mimo kruh vleku) letící dron nebo jeho naplánovaná dávka; (c) před odletem dávky: zbývající výdrž každé potřebné tyče ≥ čas dávky + rezerva 50 % (min 5 min), jinak dron neodletí a HUD řekne proč; (d) pojistka: když tyč přesto vypadne (vybitá), dron se okamžitě vrací |
| 6 mapa z vleku | Alt+7 zrušit; na vleku **pevný tablet na držáku**, R u displeje otevře plánovač (stejný režim jako ruční tablet, bez nástupu). Mini: levý kraj před bednou s dronem (x 0,55–0,90, y −0,53…0,05), Middle: sloupek `Post_L0` vpředu, Max: sloupek `Post_L0` u centrál |
| 7 kabely | Max: z truhly nahoru pod horní nosník `TopBeam_L`, dopředu k `Post_L0`, po sloupku dolů a po lemu k centrálám, s příchytkami; Middle: po předním sloupku místo volného visu; Mini: kontrola, beze změny pokud sedí |
| 8 energie | čerpadlo a mixér běží **jen při běžící centrále** (centrála se kvůli nim i nastartuje); během plnění dostanou baterie jen **50 %** výkonu; HUD „čeká na proud“ když centrála stojí / chybí nafta; totéž do simulace trasy |
| 9 nabíječka | 5 diod (červená / 2× oranžová / 2× zelená) z existujících materiálů; šikmá konzole pryč, buňka po ní = další šachta (Middle 5→6 baterií v obchodě; Max je na stropu 8, jen víc místa) |
| 10 obchod | store pack „SprayDrone“ se vším (3 vleky, tyč, tablet, kanystry); předměty zůstanou i ve své kategorii |
| 11 hnojení | ověřit ve hře bez PF a s PF; s PF doplnit zápis dusíku přes PF API (`g_precisionFarming.nitrogenMap`), herbicid s vynuceným „ne spot-spray“ |
| 12 herbicid | ověřit fáze 1–6 ve hře; spotřeba = základ × podíl plevele na pruhu (min 20 %), odhad dávky podle průměru pole |
| 13 mapa | v plánovači ikony všech tyčí (aktivní barevně, neaktivní šedě), kruhy relé jako **sjednocený obrys** s kruhem vleku; tyč dostane vanilla ikonu na velké mapě |

## Pořadí (každý krok = vlastní commit, testy u logiky)

1. **Mapa a kruhy** (1, 13) – plánovač: ikony tyčí, sjednocený obrys; kruh relé i ve světě; hotspot. Test: čistá funkce obrysu.
2. **Obchod** (10) – store pack + obrázek; ověřit ve hře.
3. **Nabíječka** (9) – 3D Middle/Max/Mini, `CHARGER_LED_BARS = 5`, export.
4. **Energie** (8) – Lua `pumpDrone`/`updatePower`/simulace; testy lupa.
5. **Kabely** (7) – 3D Max, Middle; export (lze spojit s krokem 3 do jednoho exportu).
6. **Tyč s baterií + nastoupení** (2, 4) – XML (enterable, fillUnit, kamera), Lua, i3d kamera; test.
7. **Uložení tyčí na vlek** (3) – sloty + modely držáků (Mini 1 / Middle 2 / Max 4), Lua podle bedny; export.
8. **Pojistky signálu** (5) – blokace, kontrola výdrže před dávkou, nouzový návrat; testy.
9. **Displej na vleku** (6) – model + activatable, zrušit Alt+7; export.
10. **Hnojení a herbicid** (11, 12) – nejdřív herní test (debug `coverField`), pak PF integrace a spotřeba podle plevele.

3D kroky 3, 5, 7, 9 se exportují společně (export ~25 min na vlek, na pozadí). Implementaci logiky (1, 4, 8, 10) dělají
subagenti po jednom souboru, aby se nehádali v `SprayDroneStation.lua`.

## Ověření

- `python tools/check_all.py --no-build`, `tools/lua_check.py`, lupa testy v `tmp/f/` (kruhy, energie, výdrž tyče, blokace).
- Hra (až Pavel pustí): obchod/pack, tyč (nástup, B, baterie, nabíjení na vleku), uložení R, kruhy a ikony, plnění bez
  centrály, 5 LED, kabely, displej → plánovač, hnojení bez/s PF, herbicid na poli s plevelem různých fází, prodej vleku
  s letícím dronem.

## Rizika

- Enterable na předmětu, který jde zvednout do ruky (pallet + enterable) – není vanilla vzor; záloha: nástup jen přes
  activatable bez skutečného `enterable` a HUD řádek kreslený modem.
- PF API pro dusík není ve zdrojácích celé (chybí `NitrogenMap.lua`) – zjistí se až pokusem ve hře.
- Store pack z modu: klíče v modDesc podle konvence, ne ověřené ve zdroji načítání modu.
