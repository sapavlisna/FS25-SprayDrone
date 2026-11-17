# Audit ovládání (2026-10-29)

Jen čtení, kód se neměnil. Stav pracovní kopie z 2026-10-29 odpoledne. `SprayDroneLink.lua` (tablet) a plánovač
v tu chvíli upravoval jiný agent, takže čísla řádků tam platí pro pracovní kopii, ne pro HEAD.
Vanilla klávesy jsou z `profileTemplate/inputBindingDefault_KeyboardMouse.xml`. Pavlův `inputBinding.xml` je
z 31. 8., má výchozí klávesy a žádnou akci `SDT_*` (mod tedy jede na výchozích z `modDesc.xml`).

## Vanilla konvence FS25 (výchozí klávesy)

| akce | klávesa | význam ve vanilla |
|---|---|---|
| `ACTIVATE_OBJECT` | R | pěšky i ve vozidle: aktivace nejbližšího objektu (ActivatableObjectsSystem, jedna nabídka najednou); tankování, plnění vodou, sklady |
| `INTERACT` | levé tl. | kliknutí na cílený prvek (vypínače, dveře) |
| `ACTIVATE_HANDTOOL` | levé tl. **a X** | použití drženého nástroje; s prázdnýma rukama zvednutí předmětu (HandToolHands, spouští se při puštění tlačítka) |
| `ACTIVATE_HANDTOOL_SECONDARY` | pravé tl. (a X) | hod předmětem |
| `IMPLEMENT_EXTRA` | B | **zapnout/vypnout** stroj (TurnOnVehicle) – ve vozidle / vybraném nářadí |
| `IMPLEMENT_EXTRA2` | X | **skládání** (Foldable), Ctrl+X = složit vše |
| `LOWER_IMPLEMENT` | V | spustit/zvednout |
| `TOGGLE_TIPSTATE` / `_GROUND` | I / Ctrl+I | vyklápění / vysypání na zem |
| `ENTER` | E | nastoupit |
| `MENU_ACTIVATE` / `MENU_ACCEPT` / `MENU_BACK` / `MENU_CANCEL` | Space / Enter / Esc / Backspace | menu |
| `MENU_EXTRA_1` / `_2` | X / C | menu |
| `MENU_PAGE_PREV/NEXT`, `MENU_LIST_PAGE_PREV/NEXT` | Q/E, PgUp/PgDn | menu |

Shrnuto: **R = něco s objektem, který mám před sebou, B = zapnout stroj, X = složit, levé tl. = použít to, co držím,
nebo kliknout na ovladač.**

Vlastní akce modu (`modDesc.xml:114-156`): `SDT_START_FLIGHT` Alt+8, `SDT_RETURN_HOME` Alt+0, `SDT_TOGGLE_GENERATOR` Alt+6,
`SDT_TOGGLE_LINES` Alt+5, `SDT_DRAIN_DRONE` Alt+1, `SDT_PUMP_TO_PALLET` Alt+2, `SDT_DRONE_VIEW` Alt+9, `SDT_MILL_ENGINE` Alt+7,
`SDT_MILL_OUTPUT` Alt+3 (všechny kategorie VEHICLE) a `SDT_MILL_ENGINE_FOOT` **B** (ONFOOT).

## 1. Inventura

Kontext: **P** = pěšky u objektu (ActivatableObjectsSystem, vyhrává nejbližší podle `getDistance`), **P-ruka** = pěšky s něčím
v ruce, **V** = nastoupený ve vozidle (nebo tahač s vybraným vlekem, kde je to uvedeno), **M** = v menu.

### Vleky Mini / Middle / Max

| funkce | akce | klávesa | kontext | podmínky | text | soubor:řádek |
|---|---|---|---|---|---|---|
| nastoupit do vleku | `ENTER` (vanilla) | E | P | enterable, `isTabbable=false` | vanilla | `vehicles/*/sprayDroneTrailerMini.xml:191` |
| rozložit/složit vlek | `IMPLEMENT_EXTRA2` (Foldable) | X | V (ve vleku nebo z tahače) | náklon ≤ 5° (Middle/Max), za letu se dron odvolá; Mini složit jen bez dronu na plošině (`sdt_warning_padDroneOnPlate`) | `sdt_foldObject` | `sprayDroneTrailerMini.xml:256` |
| start letu | `SDT_START_FLIGHT` | Alt+8 | **V jen ve vleku** | vybrané pole | `input_SDT_START_FLIGHT` | `SprayDroneStation.lua:5576-5578` |
| návrat domů | `SDT_RETURN_HOME` | Alt+0 | V jen ve vleku, `hasDrone` | mise běží | `input_SDT_RETURN_HOME` | `:5579-5580` |
| čáry ve světě | `SDT_TOGGLE_LINES` | Alt+5 | V jen ve vleku | – | `input_SDT_TOGGLE_LINES` | `:5581` |
| pohled z dronu | `SDT_DRONE_VIEW` | Alt+9 (C přepíná z dronu/na dron) | V jen ve vleku | dron má kameru | `input_SDT_DRONE_VIEW` | `:5572-5574`, `:5630` |
| elektrocentrála zap/vyp | `SDT_TOGGLE_GENERATOR` | Alt+6 | V ve vleku **i z tahače** | – | `sdt_action_generatorOn/Off` | `:5567`, `:5591` |
| vypustit nádrž dronu do vleku | `SDT_DRAIN_DRONE` | Alt+1 | V vlek i tahač | dron na plošině, text jen když jde | `input_SDT_DRAIN_DRONE` | `:5569` |
| přečerpat do IBC | `SDT_PUMP_TO_PALLET` | Alt+2 | V vlek i tahač | IBC do 6 m | `input_SDT_PUMP_TO_PALLET` | `:5568` |
| koncentrát do kanystrů | `TOGGLE_TIPSTATE_GROUND` (vanilla) | Ctrl+I | V vlek i tahač | v nádrži je koncentrát | `sdt_action_groundDrainOn/Off` | `:5570`, `SprayDroneToolbox.lua:1596-1640` |
| plánovač u displeje | `INTERACT` + přímý `mouseEvent` | levé tl. | P u displeje | rozložený vlek, `SCREEN_DISTANCE` | `sdt_tablet_open` | `SprayDroneLink.lua:771-776`, `:807` |
| plánovač **ze sedadla vleku** | – | **žádná** | V | – | – | (`SDT_OPEN_PLANNER` z `docs/DRON.md:524` už neexistuje) |
| bedna/stojan: víko | `ACTIVATE_HANDTOOL` (X se ručně ignoruje) | levé tl. | P | ne s předmětem v ruce, ne když cílí předmět k zvednutí | `sdt_toolbox_open` / `sdt_toolbox_dlgClose` | `SprayDroneToolbox.lua:1831`, `:1850-1871` |
| bedna: nabídka kanystrů (dialog) | `ACTIVATE_OBJECT` | R | P | `activateDistance` | `sdt_toolbox_menu` | `SprayDroneToolbox.lua:1835`, `:1880` |
| nalít z kanystru (nafta/koncentrát) | `ACTIVATE_OBJECT` (systém) | R | P-ruka (kanystr v ruce nebo ležící u hrdla) | `HAND_POUR_PLAYER` 2,2 m; přednost −1,5 m před bednou | `sdt_handPour_diesel/_concentrate/_stop` | `SprayDroneToolbox.lua:1913-1960` |
| nalít nakloněním | – (fyzika) | levé tl. zvednout, otočit | P-ruka | kanystr hrdlem nad hrdlem | `updatePourHint` | `SprayDroneToolbox.lua:~1645` |
| plošina: nasadit/sundat dron | `ACTIVATE_OBJECT` | R | P / P-ruka (dron v ruce nebo ležící) | dosah **3,2 m**, výška 3,5 m, s dronem v ruce vzdálenost 0 (přednost); Mini jen u rozložené bedny, dvě místa: bedna (přepravní, bod `sdtPadBoxPoint`, chytá do 1,5 m) a plošina (letová), vloží do bližšího; s prázdnýma rukama u druhého místa přendá (okamžitě, bez animace); složit (X) s dronem na plošině nejde → „Nejdřív přendej dron do bedny“ | `sdt_padslot_place` (Mini `_placeBox` / `_placePlate`) / `sdt_padslot_take` / Mini `_moveBox` / `_movePlate` | `SprayDronePadSlots.lua` (`getSpots`, activatable) |
| šachta baterie: vložit/vyndat | `ACTIVATE_OBJECT` | R | P-ruka (vložit) / prázdné ruce (vyndat) | 2 m, rozložený vlek | `sdt_batteryslot_put` / `sdt_batteryslot_take` | `SprayDroneBatterySlots.lua:460-534` |
| držák pumpy: uložit/vyndat | `ACTIVATE_OBJECT` | R | P / P-ruka | 2,5 m, motor pumpy vypnutý | `sdt_pumpslot_store` / `_take` | `SprayDronePumpSlots.lua:429-491` |
| držák tyče: uložit | **bez klávesy** (přijdu s tyčí v rukou) | – | P-ruka | `getAutoStore` | – | `SprayDroneRelaySlots.lua:9`, `:55-65`, `:643` |
| držák tyče: vyndat | `ACTIVATE_OBJECT` | R | P | 2,5 m | `sdt_relaySlot_take` | `SprayDroneRelaySlots.lua:662-684` |
| hadice voda/vápno: vzít, připojit, pustit, odpojit | `ACTIVATE_OBJECT` | R | P / P-ruka (konec hadice) | `PORT_DISTANCE` 1,9 m | `sdt_wh_take*`, `sdt_wh_connect*`, `sdt_wh_drop`, `sdt_wh_unplug` | `SprayDroneWaterHose.lua:1352`, `:1374-1405` |
| ventil vstupu koncentrátu | – (otevře se sám při připojení) | – | – | – | – | `SprayDroneWaterHose.lua:862`, `:923` (komentář `:4` píše o levém tl. a je zastaralý) |
| plnění vodou v rybníce | vanilla `WaterTrailerActivatable` | R | V (`getIsActiveForInput`) | vlek ve vodě | vanilla `action_refillOBJECT` | vanilla `WaterTrailer.lua:212` |
| mixér, žebřík | – (automaticky / chůzí) | – | – | – | – | `SprayDroneMixer.lua`, `SprayDroneLadder.lua:1-3` |

### Mlýnek, pumpa, násypka, tyč, kufry

| funkce | akce | klávesa | kontext | podmínky | text | soubor:řádek |
|---|---|---|---|---|---|---|
| mlýnek: motor | `SDT_MILL_ENGINE` | **Alt+7** | V (nastoupený v mlýnku) | nafta, vápno | `input_SDT_MILL_ENGINE` | `SprayDroneMill.lua:709` |
| mlýnek: výstup hadice/big bag | `SDT_MILL_OUTPUT` | Alt+3 | V | hadice nepřipojená | `input_SDT_MILL_OUTPUT` | `:717` |
| mlýnek: motor pěšky | `ACTIVATE_HANDTOOL` (viditelné) **a** `SDT_MILL_ENGINE_FOOT` (B, **skryté**) | levé tl. / B | P u rozvaděče (3,2 m) | – | `sdt_mill_start/stop` | `:794-797`, `:779-792` |
| mlýnek: výstup pěšky | `ACTIVATE_HANDTOOL` | levé tl. | P u výstupu (`MODE_DISTANCE`) | ne s předmětem v ruce | `sdt_mill_modeToBag/ToHose` | `:862`, `:842-857` |
| pumpa: motor | `SDT_MILL_ENGINE_FOOT` | **B** (viditelné) | P u motoru (2,8 m) | nafta | `sdt_pump_start/stop` (`spec.textStart/textStop`) | `SprayDronePump.lua:430` |
| pumpa: režim vstupu nádrž/rybník | `ACTIVATE_HANDTOOL` (na hadicovém activatable) | levé tl. | P u vstupní spojky | – | `sdt_pump_modeToPond/ToTank` | `SprayDroneWaterHose.lua:1358`, `:1361-1371` |
| pumpa: hadice | `ACTIVATE_OBJECT` | R | P | jako u vleku | `sdt_wh_*` | `SprayDroneWaterHose.lua:1352` |
| násypka: motor | `SDT_MILL_ENGINE_FOOT` | B | P | – | `sdt_hopper_start/stop` | `objects/hopper/limeHopper.xml:66`, `SprayDronePump.lua:430` |
| násypka, mlýnek: nasypat z pytle / nalít naftu | – (fyzika, naklonění) | levé tl. zvednout | P-ruka | – | – | `SprayDroneMill.updatePour` |
| big bag | vanilla bigBag | – (čelní nakladač / vidle) | V | – | vanilla | `objects/limeBigBag` |
| tyč: rozložit/složit | `ACTIVATE_OBJECT` | R | P (3,1 m) | ne s předmětem v ruce, stojí | `sdt_relay_unfold/fold` | `SprayDroneRelay.lua:577` |
| tyč: zapnout/vypnout | `SDT_MILL_ENGINE_FOOT` | B | P | rozložená | `sdt_relay_on/off` | `:581`, `:593-608` |
| kufr scan/sampler: víko | `ACTIVATE_OBJECT` | R | P (2,5 m od kořene) | ne s předmětem v ruce; **tablet v ruce nevadí** | `sdt_case_open/close` | `SprayDroneCase.lua:330-382` |
| kufr: vyndat/vložit baterii | `ACTIVATE_OBJECT` | R | P | **u kufru má vyndání vzdálenost 0 → přebije víko** | `sdt_batteryslot_*` | `SprayDroneBatterySlots.lua:499` |
| sampler: odeslat vzorky | `SDT_MILL_ENGINE_FOOT` | B | P u kufru | vzorky v bedničce | `sdt_sampler_send` | `SprayDroneSamples.lua:827` |
| kufr, tyč, pumpa, násypka, baterie, dron, kanystr | vanilla HandToolHands | levé tl. zvednout, pravé hodit, prostřední otáčet | P | `supportsPickUp` | vanilla | `objects/*/*.xml` (`supportsPickUp`) |

### Tablet a plánovač

| funkce | akce | klávesa | kontext | podmínky | text | soubor:řádek |
|---|---|---|---|---|---|---|
| tablet: otevřít plánovač (HEAD) | `ACTIVATE_OBJECT` | R | P s tabletem | vlek/kufr s dronem ve spojení | `sdt_tablet_open` / `sdt_tablet_noConnection` | HEAD `SprayDroneLink.lua:710-725` |
| tablet: totéž (pracovní kopie, jiný agent) | `ACTIVATE_OBJECT` s `disableConflictingBindings` + surový `keyEvent` KEY_r + surový `mouseEvent` levé tl. | R, levé tl. | P s tabletem | totéž, víc cílů | `sdt_tablet_openTarget` | `SprayDroneLink.lua:771-786`, `:807` |
| plánovač: start / zavřít | `buttonOK` / `buttonBack` | Enter / Esc | M | – | – | `gui/SprayDronePlannerScreen.xml:87-88` |
| plánovač: návrat, restart pole / odeslat vzorky | `buttonActivate` bez `inputAction` | (profil, pravděpodobně Space – **obě stejně, ověřit**) | M | – | – | `:91`, `:100` |
| plánovač: kreslení, smazat | `buttonMenuSwitch`, `buttonDelete` | podle profilu | M | – | – | `:94`, `:103` |
| plánovač: zpět | `MENU_EXTRA_2` | C | M | – | – | `:97` |
| plánovač: nastavení −/+ | `MENU_PAGE_PREV/NEXT` | Q / E | M | – | – | `:106-109`, `SprayDronePlannerScreen.lua:759` |
| plánovač: další cíl tabletu | `MENU_LIST_PAGE_PREV/NEXT` | PgUp / PgDn | M (jen tablet) | ≥ 2 cíle | `sdt_button_tabletTarget` | `:113`, `SprayDronePlannerScreen.lua:755` |

## 2. Odchylky od vanilla a nejednotnost

1. **„Zapnout stroj“ pokaždé jinak.** Pumpa a násypka: B pěšky (viditelné). Mlýnek pěšky: levé tl. (viditelné) a B (skryté).
   Mlýnek po nastoupení: Alt+7. Vanilla by tu měla B (`IMPLEMENT_EXTRA`), které je v mlýnku volné. Elektrocentrála vleku: Alt+6, a jen
   ve vleku nebo z tahače. Pěšky u centrály se zapnout nedá, přestože komentář `SprayDroneLink.lua:646` píše „elektrocentrála = INTERACT“.
2. **B pěšky (`SDT_MILL_ENGINE_FOOT`) dělá čtyři různé věci:** motor (pumpa, násypka, mlýnek), napájení tyče a **odeslání vzorků**.
   Odeslání vzorků není „zapnout“. Akce se navíc v nastavení kláves jmenuje „Mlýn zap./vyp. (pěšky)“ (`translation_cz.xml:345`),
   takže kdo si B přemapuje kvůli pumpě, hledá v nastavení mlýn.
3. **Skládání.** Vlek se skládá na X (vanilla), kufr a tyč na R. Kufr a tyč nejsou vozidla, do kterých se nastupuje, takže R je pro ně
   rozumné. Hráč ale u kufru tiskne X jako u vleku. Ve vanilla jsou pěšky skládací palety na R, takže tohle nechat a jen to popsat.
4. **Levé tl. přes `ACTIVATE_HANDTOOL` místo `INTERACT`.** Bedna, mlýnek, výstup mlýnku i vstup pumpy poslouchají `ACTIVATE_HANDTOOL`,
   který má ve vanilla i klávesu **X**. Mod to obchází tvrdým `Input.isKeyPressed(Input.KEY_x)` (`SprayDroneToolbox.lua:1849`,
   `SprayDroneMill.lua:876`, `SprayDroneWaterHose.lua:1365`). Kdo si klávesy přemapuje, tomu to přestane sedět. Displej vleku je naopak
   na `INTERACT` se surovým `mouseEvent`. Jen bedna ustoupí zvedání předmětu, na který hráč míří (`:1859-1862`). Mlýnek a výstup
   kontrolují jen to, jestli hráč už něco drží. Klik u rozvaděče, když hráč míří na kanystr, může zvednout kanystr i přepnout motor.
5. **Uložení na vlek:** tyč se uloží sama, jen když s ní hráč přijde, kdežto pumpa, dron a baterie chtějí R. Stejná věc se tak dělá
   dvěma způsoby.
6. **Řízení mise jen po nastoupení:** Alt+8, Alt+0, Alt+9 a Alt+5 fungují jen ve vleku. Plánovač se ze sedadla vleku otevřít nedá
   (`SDT_OPEN_PLANNER` zmizel), jde jen pěšky u displeje (levé tl., rozložený vlek) nebo tabletem. Ve vleku se tedy dá spustit let
   bez plánovače, ale plánovač se tam otevřít nedá. `docs/DRON.md:16`, `:519-530` pořád píše „plánovač Alt+7“, a Alt+7 je dnes mlýnek.
7. **Tablet je ruční nástroj, ale „použít“ má na R.** Vanilla nástroje v ruce (motorová pila, tlaková myčka, sprej) mají
   `ACTIVATE_HANDTOOL` = levé tl. Tablet je jediný držený nástroj, který chce R, a o R se pere s okolními objekty (viz 3.1).
8. Číslování Alt+N nemá žádný systém: mlýnek dostal Alt+7 a Alt+3, protože ty zbyly volné.

## 3. Konflikty

### 3.1 R pěšky u vleku a kufru
ActivatableObjectsSystem nabídne vždy jen **jednu** aktivaci, tu s nejmenší `getDistance`. U Mini je do zhruba 3 m plošina
(dosah 3,2 m), šachty baterií (2 m), bedna (R = dialog), hrdla pro nalévání (s bonusem −1,5 m), hadice (1,9 m) a displej. O tom, co R
udělá, rozhodují decimetry, a hráč vidí jen jeden text. U kufru má vyndání baterie vzdálenost natvrdo 0
(`SprayDroneBatterySlots.lua:499`), takže dokud je v kufru baterie, víko přes R zblízka nejde. Navíc **žádný activatable nebere
ohled na tablet v ruce**: kufr (`SprayDroneCase.lua:339-342`) i tyč kontrolují jen `hands:getIsHoldingItem()`, a tablet je
handTool, ne držený předmět.

### 3.2 Levé tlačítko pěšky
Na levém tlačítku visí vanilla zvedání předmětů (`HandToolHands` `ACTIVATE_HANDTOOL`, spouští se při puštění tlačítka), klik na bednu,
mlýnek, výstup mlýnku, vstup pumpy (všechno `ACTIVATE_HANDTOOL` při stisku), displej (`INTERACT` + surový `mouseEvent`) a v pracovní
kopii i tablet (surový `mouseEvent`). Ze systému aktivací je aktivní vždy jen jedna, ale vanilla zvedání a surové `mouseEvent` běží
vedle ní. U Mini stojí displej u bedny, takže jedno kliknutí může otevřít plánovač a zároveň otevřít nebo zavřít bednu, protože
`mouseEvent` displeje se nekoordinuje s activatable bedny.

### 3.3 B pěšky a cizí mod
Aktivní mod **FS25_handTools** registruje `HANDTOOL_TAKE` na **B** natrvalo v kontextu hráče, s `disableConflictingBindings=true`
(`FS25_handTools.zip/scripts/HandToolsSystem.lua:236`). Všechny B akce modu (`SDT_MILL_ENGINE_FOOT`) se registrují bez toho příznaku.
Kolize tak může registraci zrušit nebo vypnout. Ve hře je potřeba ověřit B u pumpy, tyče a sampleru, a jestli se v logu neobjeví
varování o kolizi. To by vysvětlilo „B někde funguje a někde ne“. Další cizí mody s R nebo B: FS25_CinemaStudio (vlastní kontext,
nekoliduje), FS25_SlurryPipeSystem (B/R ve vozidle) a FS25_TowingChain (B ve vozidle).

### 3.4 Ve vozidle
- Alt+1 a Alt+2 kolidovaly s osou tempomatu. Vyřešeno tím, že akce zůstávají aktivní (`SprayDroneStation.lua:5662-5664`).
- Nalévání z kanystru (`SprayDroneHandPourActivatable`) bere ve vozidle polohu z kořene vozidla (`SprayDroneToolbox.lua:596-603`).
  Ve vozidle u vleku tak R může nabídnout nalévání. Okrajový případ.

### 3.5 Proč R s tabletem nic neudělá
Co je doložené: `log.txt` ze hry 2026-10-29 13:37–13:44 **neobsahuje ani jedno „SDT akce: otevření plánovače letu“**. Tuhle řádku
přitom píše `SprayDroneLink:onPlayerAction` hned na začátku, ještě před kontrolou spojení. R tedy k tabletové akci vůbec nedošlo.
Kdyby šlo jen o chybějící spojení, blikalo by NO CONNECTION. Ve stejném okně je naopak 7× za sebou „kufr 1048/1050: R pěšky,
otevřít/zavřít víko“ (13:41:28–13:42:18).

Pravděpodobné příčiny, od nejpravděpodobnější:
1. **R si vzal activatable a ne tablet.** Tablet registruje vlastní `ACTIVATE_OBJECT` mimo ActivatableObjectsSystem. Kufr, šachty,
   bedna, plošina, držáky i hadice ale R nabízejí dál, i když hráč drží tablet (3.1). U kufru tak R s tabletem v ruce otevře nebo zavře
   víko, což odpovídá logu. Zdroják `InputBinding` je v `tmp/gameSource` osekaný, takže se z něj nedá ověřit, jestli při dvou událostech
   na jedné akci běží obě, nebo jen jedna.
2. **Registrace v HEAD selhala potichu.** HEAD `SprayDroneLink.lua:718-725` nekontroluje `eventId == nil`, nevolá
   `disableConflictingBindings` a nic nezaloguje. Při kolizi vazeb v kontextu hráče R mlčí. V aktivních modech jsem jinou akci na R
   v kontextu hráče nenašel, takže tohle je méně pravděpodobné. Vyloučit se to ale nedá.
3. Spojení (vlek nebo kufr v dosahu) příčinou není, viz log.

Pracovní kopie (jiný agent) přidává `disableConflictingBindings`, surový `keyEvent` na KEY_r, levé tl. a diagnostický log
(`SprayDroneLink.lua:778-786`, `:805-814`). Rizika: surové R **ignoruje přemapování** a spustí se **souběžně s activatablem**
(plánovač se otevře a zároveň se třeba přepne víko nebo vyndá baterie). `disableConflictingBindings` navíc může vypnout cizí R
v kontextu hráče.

## 4. Návrh sjednocení

**Schéma:**

| klávesa | pěšky | ve vozidle |
|---|---|---|
| **R** (`ACTIVATE_OBJECT`) | věc ↔ objekt: vzít/vložit/uložit (plošina, šachta, držáky), hadice, víko kufru, rozložit tyč, nalít, dialog bedny | vanilla (tankování, voda) |
| **levé tl.** | 1) **použít držený nástroj** (tablet), 2) kliknout na ovladač na stroji (víko bedny, tlačítko mlýnku, přepínač výstupu/vstupu, displej) přes `INTERACT`, ne přes `ACTIVATE_HANDTOOL` | – |
| **B** | zapnout/vypnout stroj, u kterého stojím (pumpa, násypka, mlýnek, centrála, tyč), akce `SDT_TOGGLE_FOOT` | `IMPLEMENT_EXTRA`: mlýnek, centrála (ve vleku nebo na vybraném vleku z tahače) |
| **X** | – | složit/rozložit vlek (vanilla) |
| **Alt+N** | – | jen mise: Alt+8 start, Alt+0 návrat, Alt+9 pohled, Alt+5 čáry, Alt+1/2 přečerpání, Alt+7 **plánovač** (vrátit) |

**Změny, od nejdůležitější:**

1. **Tablet na levé tl.** (`SprayDroneLink.lua`, `update` + `mouseEvent`/`keyEvent`): primární akcí bude `ACTIVATE_HANDTOOL`
   registrovaný jen s tabletem v ruce. S tabletem v ruce se nic zvednout nedá, takže tlačítko je volné a odpovídá vanilla
   „použít nástroj“. R z tabletu úplně odebrat i se surovým `keyEvent`. Text `sdt_tablet_open` zůstává. V popisu modu
   (`modDesc.xml:38`, `:68`, `:98`, `:40`, `:70`, `:100`) a v `sdt_droneTablet_function` změnit „R s tabletem“ na „levým tlačítkem
   s tabletem“. Pokud R zůstat musí, pak jen přes `InputBinding`, ne `keyEvent`, a všechny activatables (kufr, šachty, plošina, bedna,
   držáky, hadice, nalévání) musí v `getIsActivatable` vracet false, když `SprayDroneLink.getHeldTablet() ~= nil`.
2. **B jednotně a viditelně** (`modDesc.xml:122`, `translation_*.xml:345`): přejmenovat `SDT_MILL_ENGINE_FOOT` → `SDT_TOGGLE_FOOT`,
   text „Stroj zap./vyp. (pěšky)“. Registrovat s `disableConflictingBindings` (nebo aspoň logovat neúspěch) kvůli FS25_handTools
   na B. Mlýnek: B zviditelnit (`SprayDroneMill.lua:795`, teď `setActionEventTextVisibility(false)`). Klik na tlačítko rozvaděče
   ponechat jako fyzický ovladač.
3. **Odeslání vzorků pryč z B** (`SprayDroneSamples.lua:827`): kliknutí na bedničku vzorků (levé tl.) a tlačítko v plánovači, které
   už existuje (`SprayDronePlannerScreen.lua:899`). B tak zůstane jen na „zapnout“.
4. **Kufr: R jednoznačně** (`SprayDroneBatterySlots.lua:499`): zrušit natvrdo nastavenou vzdálenost 0. Baterii vyndávat jen
   z šachty (podle polohy šachty) a víko měřit od zámku víka, ne od kořene kufru. Text víka ukazovat vždy, když je víko blíž.
5. **Elektrocentrála pěšky** (`SprayDroneStation.lua`): B u centrály (nový activatable jako u pumpy). Ve vleku a z tahače
   `IMPLEMENT_EXTRA` (B) místo Alt+6, nebo B přidat a Alt+6 nechat jako alias. Opravit komentář `SprayDroneLink.lua:646`.
6. **Mlýnek ve vozidle** (`SprayDroneMill.lua:709`): motor na `IMPLEMENT_EXTRA` (B) jako vanilla stroje, výstup na
   `IMPLEMENT_EXTRA3` (Y) místo Alt+3. Alt+7 se tím uvolní.
7. **Plánovač ze sedadla vleku**: vrátit `SDT_OPEN_PLANNER` na Alt+7 (ve vleku jde dnes spustit let, ale ne otevřít plánovač).
   Opravit `docs/DRON.md:16`, `:519-530`.
8. **`ACTIVATE_HANDTOOL` → `INTERACT`** pro bednu, mlýnek, výstup a vstup pumpy (`SprayDroneToolbox.lua:1831`, `SprayDroneMill.lua:797`,
   `:862`, `SprayDroneWaterHose.lua:1358`). Tím zmizí obcházení `KEY_x`. Pokud `INTERACT` u Mini a Middle přebíjí zvedání předmětu
   (důvod surového `mouseEvent` u displeje, `SprayDroneLink.lua:768-770`), musí se všechny kliky chovat jako bedna: ustoupit,
   když hráč míří na předmět, který jde zvednout. Mlýnek a výstup to dnes nedělají.
9. **Tyč na vlek přes R** (`SprayDroneRelaySlots.lua:643`): samouložení vypnout nebo nechat jen jako doplněk. Hlavní cesta bude
   R s textem `sdt_relaySlot_store`, stejně jako u pumpy.
10. Planner: ověřit ve hře, jestli „Návrat“ a „Restart pole / Odeslat vzorky“ (`buttonActivate` bez `inputAction`) nesdílejí
    klávesu. Případně dát „Návrat“ na `MENU_CANCEL` nebo `MENU_EXTRA_1`.
11. Opravit zastaralý komentář o kohoutu (`SprayDroneWaterHose.lua:4`, ventil se otevírá sám).

**Co nechat a proč:** X na skládání vleku (vanilla). R na víko kufru a skládání tyče (pěšky skládané objekty ve vanilla nemají
nastoupení, R je tam běžné). R na vložení a vyndání do slotů (mod to používá všude stejně). Alt+8, Alt+0, Alt+9, Alt+5, Alt+1,
Alt+2 (mise a přečerpání nemají vanilla obdobu a Alt+N nekoliduje). Ctrl+I na kanystry (vanilla „vysypat na zem“).

## Provedeno (2026-10-29)

Celý návrh z kap. 4 je v kódu, ve hře zatím neověřený. Odchylka od návrhu: **kliky nejsou na `INTERACT`, ale na `ACTIVATE_HANDTOOL`.**
Ve vanilla `inputBindingDefault_KeyboardMouse.xml` je `ACTIVATE_HANDTOOL` = levé tl. + X, `INTERACT` = jen levé tl. Vanilla ruční
nástroje (pila, sprej, tlaková myčka) i zvedání rukama (`HandToolHands`) jsou na `ACTIVATE_HANDTOOL`, takže tablet tam patří. Kliky na
ovladače zůstaly na téže akci: `INTERACT` na stejném tlačítku zvedání rukama přebíjí (commit c7322ad, kvůli tomu vznikl surový
`mouseEvent` u displeje), kdežto další událost téže akce s ním koexistuje (bedna tak fungovala vždy). X pěšky je ve vanilla jen
klávesová obdoba téže akce. Ve vozidle, kde X skládá vlek, se žádný klik neregistruje (`SprayDroneLink.mayClick`). Obcházení přes
`Input.isKeyPressed(KEY_x)`, surové `keyEvent` (R) a `mouseEvent` (tablet, displej) je pryč.

| klávesa | pěšky | ve vozidle |
|---|---|---|
| **R** `ACTIVATE_OBJECT` | věc ↔ objekt: plošina, šachty, držák pumpy a tyče (tyč už jen přes R, samouložení zrušeno), hadice, nalévání z kanystru, nabídka bedny, víko kufru / baterie kufru, rozložit tyč. S tabletem v ruce beze změny. | vanilla (voda, tankování) |
| **levé tl.** `ACTIVATE_HANDTOOL` | tablet v ruce → plánovač; displej vleku; víko bedny; tlačítko rozvaděče mlýnku; výstup mlýnku; vstup pumpy; bednička vzorků (míří se na ni) → odeslat | – |
| **B** `SDT_TOGGLE_FOOT` (dřív `SDT_MILL_ENGINE_FOOT`) | pumpa, násypka, mlýnek, **centrála vleku (nové)**, tyč; registrace s `disableConflictingBindings` | `IMPLEMENT_EXTRA`: centrála (ve vleku nebo vlek vybraný z tahače), mlýnek |
| **Y** `IMPLEMENT_EXTRA3` | – | výstup mlýnku (dřív Alt+3) |
| **X** | (klávesová obdoba levého tl.) | složit vlek (vanilla) |
| **Alt+N** | – | Alt+7 plánovač (vráceno, `SDT_OPEN_PLANNER`), Alt+8 start, Alt+0 návrat, Alt+9 pohled, Alt+5 čáry, Alt+1/2 přečerpání; Alt+6 a Alt+3 zrušeny |
| plánovač | Space návrat, **End restart pole / odeslat vzorky** (dřív obojí Space), Enter start, Esc zavřít, X kreslení, C zpět, Backspace smazat, Q/E nastavení, PgUp/PgDn dron (tablet) | |

**Kdo dostane stisk:** u aktivací rozhoduje `getDistance` k uzlu dané věci, míření (osa kamery do 0,35 m od uzlu) odečte 1,5 m
(`SprayDroneLink.aimDistance`); text nápovědy je vždy text vybrané aktivace. Displej (levé tl.) a centrála (B) se porovnají s vybranou
aktivací (`SprayDroneLink.setSelected`, `isSelectedCloser`), vyhraje bližší a druhá akci nepřijme ani neukáže. Kliky ustupují předmětu,
na který hráč míří a jde zvednout. **Kufr:** R vyndá baterii jen při míření na ni (0,25 m) nebo do 0,6 m od ní, jinak víko; vzdálenost 0
zrušena. Bednička vzorků: dokud na ni hráč míří, kufr nejde zvednout (`getCanBePickedUp`), jinak by klik odeslal i zvedl.

**Soubory:** `SprayDroneLink.lua` (tablet, displej, centrála pěšky, sdílené `mayClick` / `mayToggle` / `registerClick` / `registerToggle`
/ `isAimedAt` / `aimDistance`), `SprayDroneToolbox.lua`, `SprayDroneMill.lua`, `SprayDroneWaterHose.lua`, `SprayDronePump.lua`,
`SprayDroneRelay.lua`, `SprayDroneRelaySlots.lua`, `SprayDronePadSlots.lua`, `SprayDronePumpSlots.lua`, `SprayDroneBatterySlots.lua`,
`SprayDroneCase.lua`, `SprayDroneSamples.lua`, `SprayDroneStation.lua`, `SprayDroneDebug.lua` (příkaz `inputInfo`),
`gui/SprayDronePlannerScreen.xml`, `modDesc.xml` (akce, popis), `translation_cz/en/de.xml`, `docs/DRON.md` (sekce Ovládání).
Test samouložení tyče (`tmp/f/test_relayslots.lua`) odstraněn s funkcí, `tools/test_batteries.py` má dva řádky na pravidlo kufru.

**Ověřit ve hře:** `inputInfo` pěšky u Mini (displej × bedna × centrála), u kufru, u pumpy a s tabletem; tablet levým tl. otevře plánovač
a R s tabletem u kufru dělá jen víko; B u pumpy, tyče, mlýnku a centrály s aktivním FS25_handTools (log bez varování `SDT_TOGGLE_FOOT`);
displej na Mini a Middle u hadice (dřív klik „spolkla“ jiná akce); zvedání kanystru u bedny a rozvaděče mlýnku (nesmí přepnout víko /
motor); kufr: míření na baterii vs. víko, bednička vzorků (poloha uzlu `caseSamples`, kufr nejde zvednout jen při míření); Alt+7 ve vleku;
B ve vleku a z tahače s vybraným vlekem; B a Y ve vozíku; End v plánovači; že se tyč s rukama u držáku sama neuloží.
