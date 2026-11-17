# Fáze 1: scénárista

**Role:** režisér-scénárista. Ručíš za příběh, rytmus a úplnost. Neřešíš, jak to hra technicky
udělá (to ověří fáze 2), ale nepiš nic, co je zjevně nemožné (viz omezení).

**Kontext:** Video k módu FS25 SprayDrone (vlek se rozloží na základnu postřikových dronů).
Tři vleky: Mini (1 dron, herbicid), Middle (hnojivo), Max (2 drony, vápno). Mapa Riverbend
Springs. Starší verze videa a záběry: `tools/cinema/edit/master.json`, poznatky
`tmp/trailer/davka_A.md`, `tmp/trailer/davka_B.md`, mód `mod/FS25_SprayDroneTrailer`
(objekty: kanystry hnojivo/herbicid/diesel, pytel vápna 50 kg, big bag, pumpa, násypka,
reléová tyč, tablet, mlýnek `sdtLimeMill`).

**Zadání (orientační):**
1. Sestava na silnici z dálky. 2. Kamera u silnice z druhé strany, otáčí se za projíždějícím
vlekem. 3. Příjezd: Middle k rybníku, Mini a Max k farmě/stodole. 4. Rozložení, pak pět
krátkých detailů vleku. 5. Plnění koncentrátem (kanystr). 6. Plánování mise: u stodoly jen
vedlejší pole, u Maxe i letový koridor. 7. Vzlet, práce z různých pohledů, přílet, doplnění a
výměna baterie. 8. Složení a odjezd.
Max navíc (beat 5m): pumpa k vleku, sání v rybníce; pumpa zmizí, hadicí se připojí mlýnek,
naplní se vápnem z big bagu, hadicí propojí s Maxem.
Látky: Max vápno, Mini herbicid, Middle hnojivo. V každé scéně jen věci daného vleku,
výjimka závěr se všemi třemi vleky vedle sebe. Produktová scéna: vedle sebe kanystry, pytel,
big bag, pumpa, násypka, reléová tyč, baterie, drony; čitelné nápisy.
Žádné titulky ani grafika.

**Výstup:** `tools/cinema/v2/scenar.md`:
- Hlavička: tři filmy (`mini`, `middle`, `max`) + `spol` (závěr) + `prod` (produkty);
  cílová délka každého filmu (návrh 90–150 s, Max delší kvůli 5m).
- Tabulka beatů společná pro všechny vleky: beat, záměr (co má divák pochopit), nálada,
  orientační délka, odchylky pro jednotlivé vleky (místo, látka, počet dronů).
- Pro každý beat a vlek seznam záběrů s ID `<vlek>-<beat>.<n>`: obsah, místo, čas dne,
  počasí, kdo/co je ve scéně, co tam být NESMÍ, typ kamery (celek/polocelek/detail), pohyb
  kamery a jeho směr, délka.
- Pět detailů vleku (beat 4) konkrétně pojmenuj podle modelu (projdi i3d/xml ve `vehicles/`).
- Tabulka „pohybová mapa": za sebou jdoucí záběry s typem a směrem pohybu; žádné dva po sobě
  jdoucí švenky stejným směrem, střídat najetí/odjetí/statiku/oblet.
- Čas a počasí drž v rámci filmu konzistentní (jeden den, posun max. pár hodin).

**Hotovo, když:** každý beat 1–8 má záběry pro všechny tři vleky, Max má 5m, existuje `spol`
a `prod`, pohybová mapa nemá konflikt, každý záběr má seznam „nesmí v záběru".
Na konec souboru napiš sekci „Otevřené otázky pro technickou kontrolu".
