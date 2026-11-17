# Fáze 4: natáčení

**Role:** technik natáčení. Spouštíš takes podle natáčecího plánu, nic nevymýšlíš.

**Vstup:** `tools/cinema/v2/natacici_plan.md`, `tools/cinema/v2/scenes/*`, `mk_take.py`.

**Před sezením:** `nvidia-smi` + `ollama ps` (GPU volné); hra běží (slot 13) přes
`tools/sdt_start.ps1`, okno mimo obrazovku; OBS běží, `obs_ctl.py status` OK; dev mód
odpovídá (`cinema_client.py ping`).

**Každý take:**
1. `python tools/cinema/v2/mk_take.py <akce> <kam>` → scéna.
2. `python tools/cinema/run_scene.py v2_<akce>_<kam> --obs`; scéna obsahuje `groundCheck`
   před záznamem a reset světa na začátku (stejné výchozí podmínky pro všechny kamery).
3. Klip přesunout do `out/trailer/v2/raw/<vlek>/<beat>/<záběr>_<kam>_t<N>.mkv`.
4. Zapsat záznam do `tools/cinema/v2/clips.json` (stav `natoceno`, log scény, telemetrie).
5. Hned předat kontrole (fáze 5). Když neprojde, opravit kameru nebo akci a natočit další
   pokus (`t<N+1>`); vadný klip do `_vyrazene/`.

**Pravidla:** natočit raději víc (rezerva 2–3 s před a po akci); u každé akce všechny kamery;
pořadí podle místa, ať se svět nepřestavuje zbytečně. Release mód neměnit; chybějící příkaz
doplnit do dev módu a přebalit (`python tools/cinema/build.py`, jen při vypnuté hře nebo
přes `reload`). Žádné ukládání savegame do slotů 1–12. Když hra spadne, restart a pokračovat.
**Hotovo, když:** všechny akce × kamery mají aspoň jeden klip ve stavu `ok`.
