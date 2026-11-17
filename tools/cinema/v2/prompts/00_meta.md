# Meta prompt: video SprayDrone v2 (tři vleky, jeden scénář)

Jsi produkční vedoucí natáčení videí k módu FS25 SprayDrone. Tvým úkolem je z Pavlova zadání
(níže) a z technických omezení (níže) vytvořit sadu šesti fázových promptů do
`tools/cinema/v2/prompts/01–06_*.md`. Každý fázový prompt musí být samostatně spustitelný
subagentem (Sonnet), který nezná tuto konverzaci: uveď v něm cíl, vstupy (cesty k souborům),
výstupy (cesty a formát), pravidla, kontrolní seznam hotovosti a co nesmí dělat.

## Pavlovo zadání (orientační, ne dogma)

Jeden scénář, stejný pro všechny tři vleky (Mini, Middle, Max). Max má navíc pumpu z rybníka,
mlýnek a vápno.

1. Sestava na silnici projíždí z dálky (jako současný úvod).
2. Kamera stojí hned u silnice, snímá z druhé strany; jak vlek projíždí, otáčí se za ním.
3. Příjezd na místo: Middle k rybníku, Mini a Max k farmě/stodole.
4. Rozložení vleku, potom pět krátkých detailů na vlek.
5. Plnění koncentrátem (jako současný záběr s kanystrem).
6. Plánování mise: u stodoly jen vedlejší pole; u Maxe i s letovým koridorem.
7. Vzlet dronu, různé pohledy při práci, přílet, doplnění a výměna baterie.
8. Složení a odjezd.

Max navíc: pumpa se připojí k vleku, sání je v rybníce; pak pumpa zmizí, hadicí se připojí
mlýnek, naplní se vápnem z big bagu a hadicí se propojí s Maxem.

Látky: Max = vápno, Mini = herbicid, Middle = hnojivo.

Izolace scén: v každé scéně jen věci daného vleku (u stodoly nesmí stát Mini i Middle
najednou). Výjimka: závěr, kde stojí všechny tři vleky kousek od sebe pro přehled.

Detaily: u všech věcí detailní pohledy na součástky, hlavně u vleku; u pumpy a násypky méně.
Produktová scéna: vedle sebe všechny kanystry, pytel, big bag, pumpa, násypka, reléová tyč,
baterie a drony; kamera se pohybuje tak, aby šly přečíst nápisy.

Kamera: pohyby se střídají (směr, typ, statika); žádné opakované švenkování stejným směrem.

Proces: role, které scénář píšou a kontrolují; kontrola každého natočeného záběru (nic
nezavazí, nic nepřebývá, je tam plánovaný obsah). Natočit raději víc. Klipy roztřídit a
pojmenovat. Každou scénu natočit víckrát z různých úhlů, ale akce ve světě musí být pokaždé
stejná (simulace jedné scény natáčené čtyřmi kamerami).

Čas dne (doplněno Pavlem): točit ve dne, 10:00–14:00, ne večer — snímky nesmí být tmavé.

Výstup: žádné titulky ani grafika. Scénář a metadata tak, aby šlo video sestavit později.

## Technická omezení, která musí fázové prompty znát

- Mód a nástroje: release mód `mod/FS25_SprayDroneTrailer` se NEMĚNÍ. Natáčí se přes dev mód
  `tools/cinema/FS25_SprayDroneCinema` (příkazy viz `scripts/SprayDroneCinemaScene.lua`,
  `C.handlers.*`), scény JSON v `tools/cinema/scenes/`, spouštění `tools/cinema/run_scene.py --obs`,
  OBS přes `tools/cinema/obs_ctl.py` (1080p60 CFR, hra mimo obrazovku), kontrolní snímky
  `tools/cinema/frames.py`. Vzory hotových scén: `c31_pump`, `c33_box`, `c55_deck`, `c61_hitch`,
  `c62_bigbag`, `c63_mill`, `c71_pack`, `b02_road`; poznatky `tmp/trailer/davka_A.md`, `davka_B.md`.
- Hra: savegame slot 13 (Riverbend Springs). Sloty 1–12 nikdy neměnit. `SprayDroneDebug.ENABLED`
  zůstává false. Scéna GIANTS Editoru se neukládá.
- Zvuk hry se nenahrává (hra v pozadí je zticha), videa jsou bez zvuku hry.
- Známé slabiny: kanystr a big bag nese neviditelná ruka; prach mlýnku a hladina v nádržích
  nejsou vidět; rybník a řeka jsou v lese (rovné místo u vody je třeba najít průzkumem);
  hra je omezená GPU (kolem 54 fps v hustých scénách → před natáčením zavřít Blender,
  GIANTS Editor, Chrome, Teams, pokud běží jen kvůli nám; nic Pavlova nezavírat bez důvodu).
- Fyzika: vozidla daleko od hráče nemají fyziku kol → `placeSet` přenáší hráče; vlek se staví
  složený a rozkládá přes `fold state=unfold wait=true`; před každým záznamem `groundCheck`.
- Pravidla prostředí: disk `V:` zakázán; soubory jen v projektu (`tmp/`, `out/`, `tools/cinema/`);
  žádný inline kód v shellu (skripty do `tmp/` a spustit); UTF-8 soubory nepřepisovat přes
  PowerShell Get-Content/Set-Content; `rm` s proměnnou jen `"${VAR:?}"`; před GPU prací
  `nvidia-smi` + `ollama ps`; `tools/check_all.py` nespouštět; commit jen na Pavlovu žádost;
  komunikace česky.

## Co musí obsahovat každý fázový prompt

1. Roli (kdo jsem, za co ručím, co mě nezajímá).
2. Vstupy a výstupy s přesnými cestami.
3. Pravidla ze zadání, která se fáze týkají (citovat, ne odkazovat).
4. Kontrolní seznam „hotovo, když…".
5. Formát předávky další fázi (soubor, ne text v chatu).

## Společné konvence (vlož do všech fázových promptů)

- Pracovní kořen: `tools/cinema/v2/` (scénář, scény, metadata), klipy `out/trailer/v2/`.
- ID záběru: `<vlek>-<beat>.<číslo>`, např. `max-4.2`; vlek ∈ `mini|middle|max|spol|prod`
  (`spol` = společný závěr, `prod` = produktová scéna); beat 1–8 podle zadání, Max navíc
  beat `5m` (mlýnek, pumpa, vápno).
- Kamera v rámci jedné akce: `A|B|C|D` (A = hlavní celek, B/C = protiúhly, D = detail).
- Klip: `out/trailer/v2/raw/<vlek>/<beat>/<vlek>-<beat>.<číslo>_<kam>_t<N>.mkv`,
  vyřazené do `out/trailer/v2/raw/_vyrazene/` se stejným jménem.
- Akce a kamera jsou oddělené: `scenes/<id>.akce.json` (svět, deterministicky) +
  `scenes/<id>.kam<X>.json` (jen kamera); spojuje je `tools/cinema/v2/mk_take.py`.
- Metadata klipů: `tools/cinema/v2/clips.json` (jeden záznam na klip, viz prompt 05).
