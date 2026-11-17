# Koncentrát, mixér, kanystry, zvuky, nádrže podle velikosti (zadání Pavla 2026-09-30)

Zdroj požadavků (Pavel):
1. Hlavní nádrže různě velké podle konfigurace 300 / 800 / 1000 / 1500 l, detailnější (inspirace vozy na vodu, plastové nádrže),
   s polepkami; napojení trubkou zůstává.
2. Menší (indukční) nádrž zůstává stejně velká, ale je **fillable**: nalévá se do ní koncentrát hnojiva nebo postřiku. Mixér při
   plnění míchá obě látky (voda z hlavní nádrže + koncentrát) a vytváří výsledný produkt.
3. Zvuk elektrocentrály a mixéru.
4. Kanystry na koncentráty (kupované herní objekty, ukládají se do slotů zadní bedny); bedna si kanystr u sebe sama vsaje, aktivací (R) se otevře a dialogem jde kanystry vybrat a nalít do nádrže.
5. Koncentrát jde z nádrže vypustit do kanystru (kvůli změně koncentrátu).

## Herní model (rozhodnuto)

Fill units vleku (pořadí v XML se nesmí měnit): **1** hlavní nádrž (fillTypes `water liquidFertilizer herbicide`, kapacita 300 /
800 / 1000 / 1500 podle konfigurace v obchodě, výchozí 1000), **2** nafta 30 l (beze změny), **3** koncentrát (vlastní fillTypes
`SDT_CONCENTRATE_FERTILIZER SDT_CONCENTRATE_HERBICIDE` z `xml/fillTypes.xml`, kapacita 50 l, `exactFillRootNode` = uzel `concentrateFillRootNode`).

Míchání (**D1**, při plnění dronu): dron se plní hotovým produktem (vanilla `liquidFertilizer` / `herbicide`, nikdy koncentrátem),
který určuje koncentrát X v nádrži (`<ratio fillType="SDT_CONCENTRATE_*" product="liquidFertilizer|herbicide">`). Když hlavní nádrž
obsahuje **vodu** a koncentrátová nádrž koncentrát X, mixér při plnění dronu bere na každý litr produktu podíl `r` koncentrátu a
`1-r` vody (`r`: hnojivo 0,25, herbicid 0,10; v XML `<mixer>` jde přepsat). Dostupná zásoba pro plán = min(voda / (1-r), koncentrát / r).
Když hlavní nádrž obsahuje rovnou hotový produkt (`liquidFertilizer` / `herbicide`), funguje vše jako dosud (bez míchání).
Vypouštění dronu zpět do vleku ukládá produkt do hlavní nádrže (jen pokud je prázdná nebo obsahuje týž produkt).

Kanystry (přepracováno 2026-09-30, obsluha znovu 2026-09-30 podle vanilla vzorů): jsou skutečné herní objekty z obchodu (hnojivo /
herbicid, 20 l, viz `docs/DRON.md`), z palet / IBC se neplní. Bedna má 12 slotů na uložení (slot = volný, nebo druh + litry, i prázdný
kanystr). Bedna nemá **žádné vlastní klávesy**:
- **Vsátí je automatické**: server jednou za 0,5 s hledá volné kanystry z modu do `intakeRadius` (1,3 m) kolem `toolboxActivateNode`
  (+0,3 m) a je-li volný slot, kanystr smaže a druh + litry zapíše do slotu; víko se krátce otevře, hráč poblíž dostane vanilla
  notifikaci. Kanystr v ruce hráče (`player.hands.spec_hands.heldItemNode`) nebo připnutý na jiném objektu se nevsává.
- **Aktivace** (vanilla „Aktivovat objekt“, hráč může mít na tlačítku myši) otevře víko a ukáže vanilla `OptionDialog` „co“
  (vybrat kanystry druhu / nalít je do nádrže / vypustit nádrž / zastavit nalévání) a případně druhý „kolik“ (1..N). Po zavření
  dialogu se víko zavře (nečinnost a odchod hráče ho zavřou i na serveru). Vylévání jde po kanystrech postupně a na víku nezávisí.
- Stav (sloty) se ukládá a synchronizuje, server ověřuje farmu a vzdálenost hráče (8 m).

## Kontrakty mezi částmi

Uzly (i3dMappings, přidat do `MAPPED_NODES` v `blender/export_car_mod.py`):
- `tankMain300`, `tankMain800`, `tankMain1000`, `tankMain1500`: skupiny s meshi hlavní nádrže dané velikosti (sedla, armatury, víko,
  polepky). Viditelnost přepíná `objectChange` v `fillUnitConfiguration` (šablona `sprayDroneTrailerCar.xml.in`).
  Výpust hlavní nádrže je u všech velikostí na **stejném místě** `MAIN_DRAIN` v `blender/sdt_contract.py`; rozvod (Pump_Suction) je
  společný. Přední konec nádrží je vždy na `MAIN_TANK_Y_FRONT`, rozměry se liší délkou dozadu a poloměrem.
- `concentrateFillRootNode`: kvádr (COL_FILL_ROOT, jako `exactFillRootNode`) kolem koncentrátové nádrže.
- `mixerMotor` (otáčivá / vibrující část mixéru), `mixerSoundNode` (empty u mixéru), `generatorSoundNode` (empty u motoru
  centrály).
- `toolboxLid` (víko bedny, pivot v závěsu; otevírá se otočením kolem lokální osy X uzlu o `openAngle` stupňů, v šabloně
  `<toolbox lidNode="toolboxLid" openAngle="105" .../>`; zavřeno = rotace 0), `toolboxCanister1..4` (kanystry v bedně, skryté podle
  obsahu, barva přes `colorScale`), `toolboxActivateNode` (empty ve středu bedny, vzdálenost pro aktivaci, střed sání kanystrů a místo výdeje).

Ostatní: zvuky vanilla vzorky přes `$data` (nic nekopírovat mimo mod), nové akce v `modDesc.xml` (`SDT_*`) s překlady cz/en, ladicí
kód pod `-- DEBUG`.

## Rozdělení práce

- **T** (Blender): 4 velikosti hlavní nádrže + polepky (vlastní atlas polepek), `sdt_bigtank.py`.
- **M** (Blender): mixér, koncentrátová nádrž (hrdlo, víko, `concentrateFillRootNode`), rozvod, bedna s víkem a kanystry
  (`sdt_tanks.py`, `sdt_mixer.py`).
- **S** (zvuky): centrála, mixér (`SprayDroneSound.lua`, `<sounds>` v šabloně).
- **L1** (Lua logika): fill units, míchání, plán / servis / plánovač, objectChange, šablona XML.
- **L2** (Lua bedna): kanystry, automatické vsátí, aktivace a dialog, uložení, synchronizace.
