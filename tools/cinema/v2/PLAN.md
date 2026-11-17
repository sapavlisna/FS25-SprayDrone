# Plán: video SprayDrone v2

Zadání a omezení: `prompts/00_meta.md`. Fázové prompty: `prompts/01–06_*.md`.

| fáze | kdo | výstup | brána |
|---|---|---|---|
| 1 scénář | subagent scénárista | `scenar.md` | — |
| 2 kontrola | 2 nezávislí subagenti (dramaturg, technik) → scénárista vypořádá | `review_*.md`, `scenar.md` v2 | žádný vysoký nález otevřený |
| 3 návrh scén | já (průzkum lokací ve hře) + subagent kameraman | `natacici_plan.md`, `scenes/*.akce.json`, `*.kamX.json` | `mk_take.py --dry` OK |
| 3b dev mód | já | chybějící příkazy v `FS25_SprayDroneCinema` | test příkazu ve hře |
| 4 natáčení | já (hra + OBS) | `out/trailer/v2/raw/...` | každý take projde fází 5 |
| 5 kontrola klipů | subagent kontrolor po dávkách | `clips.json` | stav `ok` u každé akce × kamery |
| 6 střih | já + subagent střihač | `edl/*.json`, `strih.py`, `out/trailer/v2/hruby/*.mp4` | kontaktní listy čisté |

Pořadí natáčení podle místa: farma/stodola (Mini, Max, produkty, závěr), rybník (Middle,
pumpa Maxe), silnice (beaty 1–2 všech vleků, jedno nastavení času).

Struktura:
```
tools/cinema/v2/  PLAN.md prompts/ scenar.md review_*.md natacici_plan.md
                  scenes/ mk_take.py clips.json edl/ strih.py
out/trailer/v2/   survey/ raw/<vlek>/<beat>/ raw/_vyrazene/ check/ hruby/
```
