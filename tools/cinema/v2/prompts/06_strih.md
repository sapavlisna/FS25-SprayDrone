# Fáze 6: střih (hrubý, bez grafiky)

**Role:** střihač. Skládáš tři filmy (mini, middle, max) a jejich společné části bez titulků
a grafiky. Výsledek je hrubý střih + metadata, ze kterých jde finální verzi postavit později.

**Vstup:** `tools/cinema/v2/scenar.md`, `tools/cinema/v2/clips.json` (jen `ok` a `slabsi`),
klipy v `out/trailer/v2/raw/`. Stávající render `tools/cinema/edit/render.py` použij jako
inspiraci, ne jako šablonu (je stavěný na T/P/N s grafikou).

**Pravidla:**
- Pořadí beatů 1–8 podle scénáře, u Maxe 5m po beatu 5 (nebo podle scénáře).
- Z jedné akce střídej kamery A–D (multicam): střih na pohyb nebo na změnu velikosti záběru,
  nikdy dva po sobě jdoucí záběry se stejným směrem švenku (kontroluj pohybovou mapu).
- Délka záběru 2–6 s, detaily 1,5–3 s, celky z dálky až 8 s.
- Bez textu a grafiky, prolínačky jen mezi beaty. Pracovní hudba volitelná, jen v náhledu.
- Zachovat CFR 60, 1920×1080.

**Výstup:**
- `tools/cinema/v2/edl/<film>.json`: seznam střihů `{beat, zaber, klip, in_s, out_s, prechod,
  poznamka}` pro `mini`, `middle`, `max`, `spol`, `prod`.
- `tools/cinema/v2/strih.py`, který z EDL vyrenderuje `out/trailer/v2/hruby/<film>.mp4`.
- Kontaktní list každého filmu (`out/trailer/v2/hruby/<film>_list.jpg`).
- `tools/cinema/v2/strih_poznamky.md`: co chybí, slabá místa, kde dotočit.
**Hotovo, když:** všechny tři filmy mají hrubý střih s každým beatem a list neukazuje cizí
objekty ani opakovaný směr pohybu.
