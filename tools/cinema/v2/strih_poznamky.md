# Hrubý střih v2: poznámky střihače

Výstupy: `tools/cinema/v2/edl/<film>.json` (generuje `tools/cinema/v2/edl_gen.py`), render `python tools/cinema/v2/strih.py <film|all> [--dry]`
do `out/trailer/v2/hruby/<film>.mp4` a kontaktní list `<film>_list.jpg`. Katalog všech klipů: `tools/cinema/v2/katalog.md`.

## Pravidla střihu

- Klip = poslední hodnocený take akce × kamery; `vyrazeno` se nepoužilo (starší take se nevracejí, i když byl lepší). In/out leží vždy uvnitř jednoho `nejlepsi_okno`
  (kontroluje `edl_gen.py`). Čekací smyčky (middle-let 17–47 s, max-let 22–45 s), zakryté úseky a úseky s Z9 (levitující big bag, kanystr odlétající) jsou vynechané.
- Multicam: v rámci jedné akce jdou čas klipu a kamery za sebou dopředu (bez opakování téže chvíle), kamery se střídají; žádné dva po sobě jdoucí záběry
  nemají stejný pohyb a směr (skript hlásí `POZOR`). Jediná výjimka je schválená dvojice `max-5m.3` / `5m.4` (střih na shodu, STAT na STAT).
- Přechody: tvrdý střih uvnitř beatu, `xfade 0.5` (fade) na prvním záběru každého beatu a před `max-5m.5` (mlýnek po pumpě). `spol` a `prod` jen střihy.
- Délky: celky 2–8 s, polocelky 2–6 s, detaily 1,5–3 s (u `prod` jsou záběry ~4–6 s, protože štítky potřebují statický rám).
- Bez textu a grafiky, bez zvuku (`-an`). Render: libx264 crf 18, CFR 60, 1920×1080, CPU (GPU se nepoužívá, `nvidia-smi`/`ollama ps` netřeba). Render mini ~3 min.

## Souhrn

| film | střihů | skutečná délka | cíl | chybí / slabé |
|---|---|---|---|---|
| mini | 29 | 120,5 s | ~140 s | 1.1, 3.1 (jedna kamera), kanystr barva, plánovač varování, výměna baterie |
| middle | 33 | 122,5 s | ~145 s | 6.1, otočení za vozidlem (2.1), voda ve 3.2, výměna baterie |
| max | 36 | 125,5 s | ~170 s | 3.1, 6.4, 7.3, pumpa a mlýnek slabé (hadice nevidět), 7.4 |
| spol | 4 | 23,0 s | 25 s | vše slabé (soupravy malé, cizí předměty, drony) |
| prod | 10 | 46,0 s | ~55 s | prod-7 chybí, štítky nečitelné |

Filmy jsou kratší než cíl, protože použitelná okna jsou kratší, než scénář počítal (kontrola vyřadila nebo zkrátila většinu klipů). Prodlužovat se dá až po dotočení.

## mini (29 střihů, 120,5 s)

Chybí:
- `mini-1.1` (sestava se vynořuje): `mini-silnice` A a D jsou vyřazené (keř; značka a zábrany). Film začíná rovnou 2.1 z B (PAN-L, těsný průjezd). C je rovněž PAN-L, takže nejde dát vedle B.
- `mini-3.1`: použitelný jen `mini-cesta` D (FOL), a jen 0,5–5 s (od 4 s se v pozadí objevuje cizí červený manipulátor); A, B, C vyřazené (sorgo, protisvětlo, přístřešek). Záběr je krátký a jediný.
- `mini-6.x`: červená varování v kartě pole (chybí koncentrát, přípravek) a ikony cizích vozidel v celém záběru (Z5); displej se vizuálně nerozsvěcuje.
- `mini-7.6` a `7.7`: doplnění nádrže a výměna baterie se z použitých záběrů nepoznají (plovoucí baterie Z9 vynechána).

Slabá místa: `mini-5.x` kanystry v bedně jsou zelené, kanystr herbicidu oranžový; `mini-7.2` mlha bílá, ne bílomodrá; `mini-3.2` souprava na dvoře malá (10–12 % šířky).

Doporučené dotočení (akce / kamery):
- `mini-silnice` A, D (A: x −40 nebo −70, z ≈ −659 nebo y 1,8; D: x ≈ −65 nebo −95, nebo druhá strana silnice) pro 1.1.
- `mini-cesta` A, B, C (A z pole sorga na kraj cesty ~25 m od štěrku; B z opačné strany, slunce za kamerou, bez plotu; C ven z přístřešku o ≥ 8 m na západ); D: `isolate` červeného manipulátoru ze stodoly.
- `mini-planovac` A, B po doplnění koncentrátu (herbicid 50 l) a výběru přípravku, ikony cizích vozidel pryč.
- `mini-navrat-servis` B, C, D: kamera výš a dál, aby bylo vidět dron i truhlu s bateriemi současně (výměna baterie); C na dron a truhlu místo na centrálu.
- `mini-kanystr` (akce): barva kanystrů v bedně = herbicid (oranžová).
- Volitelně `mini-dvur-prijezd` A (zábradlí) a C (kráva), `mini-slozeni-odjezd` B (ohrada).

## middle (33 střihů, 122,5 s)

Chybí:
- `middle-6.1` (displej): `middle-planovac` A i B mají v prvních sekundách listí přes obraz; použity jsou jen 6.2 a 6.3. 6.x má červená varování a ikony cizích vozidel (Z5).
- `middle-2.1` (otočení za vozidlem do 3/4 zezadu): PAN-L je jen v B (průjezd), A a D jsou statické; po průjezdu se souprava vzdaluje bez kamery za ní.
- Voda ve `middle-3.2` je jen v D (souprava malá), B je bez vody a s listím vlevo dole.
- `middle-7.4` je externí pohled, ne z palubní kamery; `7.6/7.7` výměnu baterie ukazuje jen B (9–12 s) s plovoucí baterií (Z9).

Slabá místa: `middle-5.2` kanystr visí bez opory (animace hry, Z9); `middle-8.2` jen klip C, ostatní kamery zakryté keři; `middle-4.4` jen shora na truhlu (sloty špatně vidět).

Doporučené dotočení:
- `middle-planovac` A, B (6.1 z místa bez listí, koncentrát a přípravek nastavit, `isolate` ikon).
- `middle-polo-prijezd` A (keř, strom vpravo), B (otočit k hladině, o 2 m od keře), C (ven z keře ~8–10 m, y 1,8 m); D je v pořádku.
- `middle-silnice`: samostatný záběr 2.1 s PAN za vozidlem (A, D jsou statické).
- `middle-navrat-servis` A, D: doplnit záběr na truhlu a výměnu baterie; `middle-let` A, C (C: víko truhly zakrývá 0–3 s, větev nad vodou) a zkrátit čekání 17–47 s v akci; zkusit palubní kameru dronu pro 7.4.
- `middle-slozeni-odjezd` A, B (8.2 blíž k cestě odjezdu, mimo keře); `middle-rozlozeni` B (keř vlevo).

## max (36 střihů, 125,5 s)

Chybí:
- `max-3.1` (odbočka ze silnice a jízda po trávě k potoku): akce nemá pokrytí (hlásí i `gen_main.py`). Film jde ze 2.1 rovnou na 3.2.
- `max-6.4` (fialová letová plocha): v klipech je plocha hotový trojúhelník od začátku, s červenou hláškou „Vlek stojí mimo letovou plochu“ (Z5) a mapa se nehýbe; nepoužito.
- `max-7.3` (TOP): stopa vápna se shora nezobrazí (A 32 m, B 110 m, C 48 m); okno kontroly 7.3 vůbec nepokrývá.
- `max-7.4`: jeden dron, bez mlhy, nad zeleným polem místo strniště, Max nevidět.

Slabá místa:
- `max-5m.1`–`5m.4` (pumpa): pumpa je 2–5 % šířky, hadice (sání do potoka, výstup na ventil A) a cedulky VSTUP/VÝSTUP nejsou vidět, „zmizení“ pumpy v 5m.3 → 5m.4 je špatně čitelné.
- `max-5m.5`–`5m.8` (mlýnek): hadice mlýnek → vápnová spojka a svítící prstenec nikde vidět; big bag levituje na nebi (Z9), použit jen okamžik u mlýnku (9–10,5 s) a proud vápna (16–17,5 s); nechybí tak vyklopení big bagu do mlýnku v souvislém záběru.
- `max-4.3` (A má listí v popředí, použito B: vlek s plachtami v pohybu, kolejnice zblízka chybí), `max-4.4` (plošina s dronem shora, truhla a navíječe v záběru nejsou), `max-4.6` (vápnová spojka se nečte).

Doporučené dotočení:
- 3.1: natočit novou akci (odbočka a jízda po trávě podél pole k potoku, kamery podél pole, TRK L→R); `max-zaparkovani` A, B, C (3.2) jsou slabé, použit jen D.
- `max-pumpa` A, B, C, D: pumpa k hraně potoka, kamera ~4 m (fov 25–30), ověřit vykreslení hadic po připojení, cedulky ke kameře; C přesunout na pás mezi Max a potok.
- `max-mlynek` A, B, C: přidat hadici mlýnek → spojka Maxu; big bag nechat klesnout do záběru s mlýnkem (kamera ze strany, ne z nebe); 5m.8 s napnutou hadicí a svítícím prstencem.
- `max-planovac` A, B: letová plocha tak, aby vlek byl uvnitř (bez červené hlášky), postupné přidávání bodů s posunem mapy doprava; schovat ikony vozidel.
- `max-let` A, B, C: 7.3 snížit (A ~20 m, B ~35 m, C zapnout postřik před záběrem), 7.4 nad strniště, odstranit čekání 22–45 s.
- `max-detaily` A, B (4.2/4.3 keř; 4.4 kamera zpět k truhle a navíječům; 4.6 keř před ventily); `max-navrat-servis` A, B (7.5 z keře; 7.7 kamera 3,6 m nad truhlou).

## spol (4 střihy, 23,0 s)

Použito vše, co kontrola připouští (A 6,5–13, 14–20, 24,5–31; B 31–35). Slabá místa: soupravy jsou malé (~8–10 % šířky) a vidět jen jako siluety, vlevo na dvoře leží kanystry a pytel z `prod` (Z2),
v B jsou na pastvině krávy (Z3) a cizí pytel, drony jsou ve vzduchu jen v prvním záběru a v JIB-U už nejsou v záběru.

Dotočit `spol` A, B: odstranit kanystry, pytel a krávy z dvora; start a konec kamery z porostu/břízy/stodoly ven; TRK a JIB vést blíž (vleky ≥ 25 % šířky); drony držet v záběru (`droneHover` do konce JIB).

## prod (10 střihů, 46,0 s)

Chybí `prod-7` (tři vleky s drony S, M, L): `prod-vleky` má jediný použitelný klip A t1 a ten v okně pokrývá jen `prod-1` a `prod-6` (záznamy A t2 a B t1 skončily chybou, bez souboru).
Slabá místa: čelní strany kanystrů jsou hladké, HNOJIVO / HERBICID / nafta se nepřečtou, jen barva; pytel je vzhůru nohama a dole ořezaný; texty VSTUP / VÝSTUP / VÁPNO na pumpě a násypce nečitelné;
zelený LED na reléové tyči jen drobný bod; baterie v truhle `prod-6` nejsou jasně vidět; vleky v `prod-1` jsou drobné tmavé siluety, drony S/M/L nerozlišitelné.

Dotočit: `prod-rada` A, B (štítky kanystrů, pytel nápisem ke kameře, cedulky pumpy a násypky zblízka, vyšší kontrast LED); `prod-vleky` A, B (kamera na volný beton přímo před vleky, výš ~2 m a blíž ~12 m pro `prod-7` a `prod-1`; `prod-6` zblízka shora do šachet s bateriemi).
