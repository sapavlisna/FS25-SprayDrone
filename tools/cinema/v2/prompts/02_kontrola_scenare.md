# Fáze 2: kontrola scénáře (dvě nezávislé role)

Spouští se dvakrát, jako dva oddělení subagenti; každý píše vlastní soubor. Nevidí se navzájem.

## 2a Dramaturg

**Role:** hlídáš, že scénář splňuje zadání a drží se ho; nejsi technik.
**Vstup:** `tools/cinema/v2/scenar.md`, zadání v `tools/cinema/v2/prompts/00_meta.md`.
**Kontroluj:** všech osm beatů u všech tří vleků; Max má pumpu z rybníka → mlýnek → big bag →
hadice do Maxe; látky (Max vápno, Mini herbicid, Middle hnojivo); izolace scén (žádný cizí vlek
mimo závěr); Middle u rybníka, Mini/Max u farmy; u stodoly plán jen na vedlejší pole, u Maxe
koridor; pět detailů vleku; výměna baterie i doplnění; produktová scéna s čitelnými nápisy;
střídání pohybů (pohybová mapa); žádné titulky ani grafika; délky přiměřené.
**Výstup:** `tools/cinema/v2/review_dramaturg.md`: seznam nálezů (závažnost vysoká/střední/
nízká, ID záběru, problém, návrh opravy).

## 2b Technik proveditelnosti

**Role:** znáš hru a dev mód; ověřuješ, že každý záběr jde natočit.
**Vstup:** `scenar.md`; příkazy dev módu `tools/cinema/FS25_SprayDroneCinema/scripts/*.lua`
(`C.handlers.*`), ladicí funkce release módu `mod/FS25_SprayDroneTrailer/scripts/SprayDroneDebug.lua`
(jen čti), vzorové scény `tools/cinema/scenes/c*.json`, poznatky `tmp/trailer/davka_A.md`,
`davka_B.md`.
**Pro každý záběr urči:** proveditelné hned / chybí příkaz (popiš jaký, v dev módu) / nejde
(navrhni náhradu). Hledej zejména: sání pumpy v rybníce (`whPond`) a rovné místo u vody,
odebrání pumpy, napojení mlýnku hadicí na Max, plnění big bagem, zobrazení letového koridoru
v plánovači, výměna baterie viditelně, izolace (odebrání ostatních vleků a strojů ze scény),
deterministické opakování akce pro více kamer (AI jízda a drony nejsou úplně
deterministické → navrhni, jak výsledky sesynchronizovat).
**Výstup:** `tools/cinema/v2/review_technik.md`: tabulka záběr → stav → co je potřeba;
souhrn chybějících příkazů s odhadem náročnosti.

## 2c Revize scénáře

Scénárista zapracuje oba posudky do `scenar.md` (zvýšit verzi v hlavičce) a do
`tools/cinema/v2/review_vyporadani.md` napíše ke každému nálezu: přijato / zamítnuto + proč.
**Hotovo, když:** žádný nález s vysokou závažností nezůstal bez vypořádání.
