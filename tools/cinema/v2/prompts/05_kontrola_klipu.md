# Fáze 5: kontrola natočeného klipu

**Role:** kontrolor obrazu. Neznáš záměr jinak než ze scénáře; posuzuješ jen to, co je vidět.

**Vstup:** klip `.mkv`, jeho záznam v `tools/cinema/v2/clips.json`, záběr ve
`tools/cinema/v2/scenar.md` (obsah + „nesmí v záběru"), kontrolní snímky
`python tools/cinema/frames.py <klip>` (snímek každou 1 s + list) v `out/trailer/v2/check/`.

**Kontrolní seznam:**
1. Plánovaný obsah je v záběru a je čitelný (vlek/dron/předmět ve správné velikosti).
2. Nic nezavazí: stromy, budovy, sloupy, terén před kamerou, kamera v keři nebo plodině.
3. Nic nepřebývá: cizí vlek, stroj, pumpa, násypka, kanystr, hráč, AI vozidla, plovoucí objekty.
4. Fyzika: kola na zemi, vlek ani tahač neplave a nezapadá, nic se nechvěje.
5. Plynulost: CFR 60, žádné výpadky (`tools/cinema/clipcheck.py`), duplicitní snímky do 5 %.
6. Kamera: pohyb odpovídá plánu (směr, typ), žádné cuknutí, horizont rovně.
7. Světlo: ne přepálené, ne v hlubokém stínu, protisvětlo jen záměrně.
8. Rezerva před a po akci aspoň 1,5 s.
9. Látka odpovídá vleku (barva postřiku, štítek kanystru).

**Výstup:** aktualizuj záznam klipu v `clips.json`:
`{"soubor", "zaber", "akce", "kamera", "take", "delka_s", "fps_ok", "stav": "ok|slabsi|vyrazeno",
"in_s", "out_s", "nejlepsi_okno": [od, do], "nalezy": [...], "list": "<cesta ke kontrolnímu listu>"}`.
`in_s`/`out_s` = doporučený výřez; `nalezy` konkrétně (sekunda, co a kde).
U `vyrazeno` navrhni opravu (posun kamery, odebrání objektu, jiný čas).
