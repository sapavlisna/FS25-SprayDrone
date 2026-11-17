# Fáze 3: návrh scén (kameraman + lokační skaut)

**Role:** kameraman. Ze scénáře uděláš natáčecí plán: akce ve světě + 2–4 kamery na akci.

**Vstup:** `tools/cinema/v2/scenar.md` (po revizi), `review_technik.md`, průzkumné snímky
lokací (`out/trailer/v2/survey/`, pořizuje `tools/cinema/survey.py` ve hře), vzorové scény
`tools/cinema/scenes/*.json`.

**Princip více kamer:** jedna akce = jeden soubor `tools/cinema/v2/scenes/<akce>.akce.json`
se stejným nastavením světa (čas, počasí, pole, umístění vozidel, odebrání cizích vozidel)
a stejnou časovou osou akce. Ke každé akci 2–4 soubory `<akce>.kamA.json` … `kamD.json`,
které obsahují jen kamerové příkazy (`camPath`, `camSet`, `camFollow`, `camOrbit`) s časem od
značky `{"mark": "akce"}`. `tools/cinema/v2/mk_take.py` je spojí do spustitelné scény
`tools/cinema/scenes/v2_<akce>_<kam>.json`. Akci nikdy neupravuj kvůli jedné kameře; když
kamera potřebuje jinou akci, je to jiná akce.

**Pro každou akci napiš:**
- ID akce (např. `max-4_rozlozeni`) a seznam záběrů ze scénáře, které pokrývá.
- Souřadnice a natočení vozidel; čím izolovat (`removeVehicle` všech cizích vleků/strojů,
  pumpy, násypky, mlýnku, cisteren).
- Kamery A–D: typ (celek, protiúhel, detail), dráha, ohnisko (fov), směr pohybu, výška.
  V rámci akce pokryj aspoň dva různé směry a jeden statický nebo téměř statický záběr.
- Předpokládané in/out pro střih (které sekundy akce jsou užitečné).
- Rizika: co může zavazet (stromy, budovy, cizí stroje), slunce v protisvětle.

**Produktová scéna `prod`:** objekty v řadě na rovném betonu (kanystry hnojivo, herbicid,
diesel; pytel vápna; big bag; pumpa; násypka; reléová tyč; baterie; Mini dron, Max drony).
Kamera pomalu, blízko (fov 25–35), u každého předmětu chvíli stát, aby šel přečíst štítek;
střídat směr jízdy podél řady.

**Výstup:** `tools/cinema/v2/natacici_plan.md` (tabulka akcí a kamer, pořadí natáčení
seskupené podle místa a nastavení světa) + soubory akcí a kamer v `tools/cinema/v2/scenes/`.
**Hotovo, když:** každý záběr scénáře je pokrytý aspoň dvěma kamerami (kromě detailů, kde
stačí jedna kamera ve dvou variantách), `mk_take.py --dry` projde všechny kombinace.
