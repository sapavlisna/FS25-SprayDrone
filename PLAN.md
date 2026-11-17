# FS25 — postřikový dron se servisním vlekem

Vlastní mód do Farming Simulator 25: vlek, který se na poli rozloží a slouží jako základna
pro postřikové drony. Stavíme od nuly včetně modelování v Blenderu.

Založeno 2026-09-15.

## Inspirace a stav světa

Předlohou je reálná profesionální sestava pro DJI Agras (T40/T50/T100): přívěs, na něm
elektrocentrála, zásobní nádrž na vodu, míchací kužel na koncentrát, nabíječky, dva drony,
RTK mobilní stanice a tablet pro naklikání mise.

**Ve FS25 takový mód neexistuje.** Prohledáno: ModHub, KingMods, Mod-Network, Modhoster,
FS25.net, itch.io autora.

Nejblíž je **Agro Drone – AeroSpray** (Level55 Games, v1.1.0.1 ze 4. 9. 2026,
distribuce mimo ModHub přes https://level55.itch.io):

- modely S45L / S70L / S100L / S2000L Unreal (45–2000 l, $22k–$40k)
- záběr 10 m, dávka ~14 l/ha, doporučená rychlost 15–18 km/h, max 35 km/h
- autonomní postřik: detekce pole, paralelní linky, automatické otočky
- **rozpozná už ošetřené plochy a přeskočí je** — a tím řeší i persistenci
- baterie 24 kWh, vyjímatelné packy, return-to-home při vybití i prázdné nádrži
- ALE: výměna baterky i plnění jsou **ruční**, žádný vlek/základna, start mise z dronu

To, že i placený mód nechal výměnu baterky ruční, je varovný signál — ne náhoda.

## Návrh (Pavlův, po úpravách)

### Vlek

**Zdroj předlohy (2026-09-15):** referenční fotky reálných trailerů (nuWayAg, Drone Deer
Recovery) ukázaly, že skutečná sestava se **nikde nesklápí** — je to tuhá svařená konstrukce:
gooseneck přívěs, tandem náprava, dole rovná ložná plocha s nádržemi (kapsle/válce) a boxy
generátorů napevno přišroubované, šikmé vzpěry (do V) nesou zvýšenou plošinu nad tím vším
s trubkovým zábradlím, drony sedí přímo na plošině, přístup žebříkem.

Původní návrh „rozloží se plachta na střeše" tomu neodpovídal — zjednodušeno:

- **rozložení = zaparkováno + zabrzděno** (spuštěné patky/brzda), žádná animace kapotáže
- volitelně jeden kosmetický prvek animace: **sklápěcí schůdky/žebřík** (jeden hinge,
  nezávislé na zamykací logice, jen „pocit" aktivace)
- nádrž, centrála, plošina pro drony jsou **napevno v modelu** — žádné attachables,
  žádná fyzika navíc, kapacita jen v XML
- drony sedí nahoře na plošině; po přistání všech se vlek znovu připojí k tahači a odjede
- nad plošinou (nad drony) **statická plachta/stříška** na sloupcích — ochrana před deštěm,
  žádná animace, jen plochý panel nesený pár tyčemi po rozích plošiny

Zaparkovaný a zabrzděný = statický cíl → **odpadá přistávání na pohyblivý objekt**, což byl
největší technický risk celého záměru — a odpadá i dřívější „otevřená otázka #2" (jak base
game zamyká rozložený stroj), protože žádný zámek na animaci teď není potřeba, jen
`brakeForceScale`/`parkVehicle` stav.

### Rozměry drona (reálné DJI Agras, pro rozměry plošiny)

Pavel zvažuje T50 nebo T100. Rozměry v konfiguraci „ramena rozložená, vrtule složené"
(dron stojí na vleku připravený mezi lety — relevantní pro rozteč na plošině):

| Model | Rozteč (D×Š) rozložená ramena, složené vrtule | Výška | Nádrž | Doba letu |
|---|---|---|---|---|
| T50 | 1590 × 1900 mm | 820 mm | 40 l | 7–10 min |
| T100 | 1820 × 1840 mm | 975 mm | 100 l | 8–10 min |

Pro plošinu počítat s cca **2 × 2 m na dron** (rezerva na okraje/zábradlí), rozestup mezi
drony přidat zvlášť. T100 má 2,5× větší nádrž při podobné době letu → míň návratů na dávku,
ale těžší a dražší dron. **Zatím nerozhodnuto který** — rozměry plošiny navrhnout tak, aby
šly oba (menší T50 se jen ztratí v rezervě). Vše orientační, neřešit přesně.

Drony na plošině **vizuálně odlišit** (barva/označení), ať jde v mise poznat, který je který.

**Nápad (2026-09-15, zvážit místo/vedle statické stříšky):** skládání by nemuselo být na
vleku vůbec — reálné Agras drony už mají skládací ramena (viz tabulka výše, stav „ramena
složená"). Po přistání a zajištění by se tedy mohla složit **ramena samotného dronu** +
přes něj hodit **popruh** (tie-down), místo skládání přívěsu nebo stříšky nad drony.
Kosmetická animace na dronu, ne na vleku — nerozhoduje o zamykací logice.

### Dosah — limitem je nádrž, ne baterka

Na číslech AeroSpray: 70 l při ~14 l/ha = **5 ha na nádrž**. Baterka 24 kWh při 15–18 km/h
vydrží skoro jistě déle. Dron se tedy bude vracet kvůli postřiku, ne kvůli energii.

Proto **dávkování je hlavní mechanika, ne fallback**: mise se předem rozseká na dávky, kde
jedna dávka = co dron zvládne na jednu nádrž (nebo baterku, podle toho co dojde dřív,
včetně letu tam a zpět). Dron odletí dávku, vrátí se, doplní, letí na další.

**Kružnice dosahu** zůstává jako sanity kontrola na startu: „nejvzdálenější roh pole je dál,
než dron doletí a vrátí se s rezervou" → misi nelze spustit, přeparkuj vlek. Bez dávkování
by kružnice omezila mód jen na malá pole.

### Persistence — neukládat pozici dronu

FS25 ukládá sám na interval (autosave), i v multiplayeru. Kdyby se dron po načtení
teleportoval z půlky pole domů, hráči to budou hlásit jako bug.

Řešení: **neukládat pozici dronu ani rozpracované linky vůbec.** Uložit jen
`{rozloženo, ID pole, mise aktivní}`. Při načtení dron spawnout na vleku a misi přepočítat
z **aktuálního stavu pole** — hra si sama pamatuje, co je nastříkané, takže generátor vyrobí
linky jen tam, kde ještě něco chybí, a dron plynule pokračuje.

Stav k uložení je pár hodnot a nemůže se rozejít s realitou.

### Courseplay — nepoužívat

Courseplay FS25 je živý (v8.1.x, aktivní vývoj), ale:

- jeho generátor je pro **pozemní** techniku: souvrať, poloměr otáčení, couvání, překážky —
  dron nepotřebuje nic z toho
- naopak neumí, co dron potřebuje: výšku letu, přerušení řádku uprostřed a návrat domů,
  segmentaci na dávky
- zbyla by z něj jen detekce polygonu pole, kterou FS25 umí nativně (a AeroSpray ji dělá bez CP)
- cena závislosti: API je rozpracované (course editor je právě vypnutý a má se vrátit),
  každý jejich update může rozbít mód

Boustrophedon přes polygon pole **bez kinematiky** je pár stovek řádků Lua — méně práce než
učit se cizí API a pak ho hlídat.

## Rozdělení práce

| Vrstva | Podíl | Poznámka |
|---|---|---|
| Lua logika (plánování, let, přistání, výměna, stavový automat, MP sync) | ~70 % | těžiště |
| UI ovládací plošiny (mapa, výběr pole, nastavení mise) | ~15 % | vlastní GUI nad `g_currentMission` |
| Modely (vlek, dron, centrála, nádrž) | ~15 % | hranatá technika, parametricky přes `bpy` |

## Etapy

### 0. Toolchain

Instalačky a Blender jsou v **`E:\FS25-edit`**.

> **Oprava 2026-09-27:** pracuje se v **Blenderu 5.1.2** (`E:\FS25-edit\blender-5.1.2-windows-x64\blender.exe`),
> ne v 4.3.1. Oficiální GIANTS exportér 10.0.x sice chodí jen na 4.2/4.3, ale komunitní
> https://github.com/dtapgaming/GiantsExporterRework-Blender (GPL-3) podporuje Blender 5. A díky 5.1
> jde použít `blender-i3d-importer` (v Blenderu už nainstalovaný jako extension) — vanilla modely
> se dají načíst přímo do scény jako reference. Body níže o 4.3.1 a škrtnutém importéru neplatí.
>
> **Exportér nainstalován 2026-09-27:** komunitní GiantsExporterRework **10.0.16** (stabilní), ale se
> zaměněným **oficiálním `i3dConverter.exe`** z podepsané instalačky GIANTS `blender_i3d_export_10.0.2_win.exe`
> (SHA-256 `BA2A1847…`). Komunitní převodník (`43C9680D…`, nepodepsaný, jiný než oficiální) se nepoužívá.
> Zdrojové balíčky v `tools/`. Aktualizace exportéru vypnuté, Blender má online access vypnutý.
> Zkušební export malého vleku do `out/export_test/` ověřen zpětným importem (147/147 dílů, odchylka ≤ 1 mm,
> čep spojky na +Z jako u vanilla). Nastavení: `BAKE_TRANSFORMS` = (x, y, z) → (x, z, −y) po uzlech.

- [x] **Blender 4.3.1** portable — `E:\FS25-edit\blender-4.3.1-windows-x64\blender-4.3.1-windows-x64\blender.exe`
- [x] **Blender MCP** (komunitní) — nastaveno, viz níže
- [ ] **GIANTS Blender Exporter Plugins 10.0.2** — stažený byl omylem 10.5.0 (Project Motor
      Racing), nutno nahradit. Zatím není potřeba.
- [ ] **GIANTS Editor 10.0.13** z https://gdn.giants-software.com/downloads.php
      — **žádný editor nainstalovaný není.** Zbyla jen uživatelská složka po odinstalovaném
      9.0.6 (`C:\Users\Pavel\AppData\Local\GIANTS Editor 64bit 9.0.6` — jen `editor.xml`, log,
      `scripts`, `shader_cache`; žádné `.exe`). Instalační adresář
      `C:\Program Files\GIANTS Software\GIANTS_Editor_9.0.6_64-bit\` z konfigurace **neexistuje**
      a v registru není nic. Poslední spuštění: 30. 5. 2025, nad FS22 mody v `E:\FS22-Mods\HB-EDIT`.
- [ ] volitelně `blender-i3d-importer` — https://github.com/nadine-brinkmann/blender-i3d-importer

FS25 samotný je OK: `E:\SteamLibrary\steamapps\common\Farming Simulator 25`, **verze 1.23.1.0**.
Mody jsou v `E:\SteamLibrary\FS25-Mods` (ne v Documents).

#### Nákupní seznam z GDN

https://gdn.giants-software.com/downloads.php (vyžaduje účet)

**Nutné teď — 58 MB:**

- [ ] GIANTS Editor **v10.0.13** (41,40 MB)
- [ ] Blender Exporter Plugins **v10.0.2** (16,13 MB)

> **Pozor na řadu 10.5.x.** Na GDN jsou i Editor v10.5.1 (74,12 MB) a Blender Exporter v10.5.0
> (18,40 MB), ale podle všeho patří k **Project Motor Racing**, ne k FS25 — GDN teď slouží
> oběma hrám (je tam i „Project Motor Racing Livery UV Templates"). Nepotvrzeno natvrdo,
> proto si u souboru přečíst popis. Pro FS25 je řada **10.0.x**.

**Malé a vyplatí se:**

- [ ] VS Code – Farming Simulator IDE Support (Lua je ~70 % projektu, děláme ve VS Code)
- [ ] Scripting Farming Simulator with Lua eBook PDF (4,54 MB)
- [ ] GIANTS Editor LUA Script Snippets (39 KB), LUA Sheet PDF (45 KB)
- [ ] GIANTS Editor Shortcuts PDF English (66 KB)
- [ ] Vehicle Material System (1,22 MB) — jak FS25 řeší materiály na technice
- [ ] Mod Icon Template (17 KB)

**Až u příslušné etapy:**

- GIANTS Texture Tool v9.0.1 (4,42 MB) — DDS konverze, až se bude texturovat
- Effects HowTo PDF (3,00 MB) + Samples (4,42 MB) — **etapa 3**, postřikový efekt
- FS25 Icon Generator v10.0.4 (43,29 MB) — ikona do obchodu, až na konci
- FS25 Test Runner v0.9.20 (11,26 MB) — automatizované testy módu
- GIANTS Studio v10.0.2 (9,76 MB) — vlastní IDE s Lua debuggerem, jen pokud VS Code podpora nestačí
- Blender Source Textures (504,84 MB) — velké, stahovat až když bude jasné, že jsou potřeba
- Loop Synthesis Tool v10.0.1 (8,36 MB) + Samples (2,16 MB) — zvuk vrtulí, daleko

**Nebrat:** Maya a 3ds Max exportery, všechny verze 9.x/8.x a FS22 věci, DEM Converter,
GRLE Converter, BuildingArray Map Europe/America (185 a 250 MB — tvorba map, my mapu neděláme),
Project Motor Racing UV Templates (854 MB, jiná hra), Crawlers Samples (pásové podvozky),
Texture Assemble. „Modding for Dummies" a „Art of Modding" jsou úvodní brožury, u tohohle
projektu nic nedají.

#### Dokumentace zdarma přímo ve hře

`E:\SteamLibrary\steamapps\common\Farming Simulator 25\sdk\` obsahuje:

- `xmlDoku\` se schématy — pro nás hlavně **`vehicleTypes.xml`, `specializations.xml`,
  `placeableTypes.xml`**, dále `inputActions.xml`, `storeCategories.xml`, `guiProfiles.xml`
- `collisionMasks.txt` — kolizní masky (potřeba u rozloženého vleku i u dronu)
- `scriptBindingChanges.txt` — změny script bindingů mezi verzemi
- `maps\`, `debugger\`

Nic z toho se nemusí stahovat.

#### Místo na disku

Celý toolchain je pod 2 GB: Editor ~40 MB (bere si data z instalace hry), exporter 16 MB,
Blender ~1–1,5 GB rozbalený.

Stav disků k 2026-09-15: C: 57,5/441,9 GB volno (13 %), D: 29,9/488,8 GB (6,1 %),
E: 125,6/465,8 GB (27 %). C+D je jeden NVMe zaplněný z ~90 % — viz [[lightroom-disky]].
→ **Instalovat všechno na E:.** Blender vzít jako portable ZIP a rozbalit na E:, vyhne se to
zápisu do `C:\Program Files`. GIANTS Editor má volbu cesty v instalátoru.

#### Blender MCP — nastaveno 2026-09-15

Použit **komunitní** https://github.com/ahujasid/blender-mcp. Oficiální Blender Lab MCP
vyžaduje **Blender 5.1+**, takže na 4.3 nejde vůbec — a i kdyby, umí scénu hlavně číst
(polycount, materiály, přejmenování datablocků), ne tvořit geometrii.

- server: `E:\ClaudeProjects\FS25-SprayDrone\.venv\Scripts\blender-mcp.exe` (blender-mcp 1.9.4,
  vlastní venv jako u ProxmoxMCP, bez globální závislosti na `uv`)
- registrace: `claude mcp add blender --scope user -e BLENDER_MCP_SAFE_MODE=1
  -e BLENDER_MCP_DISABLE_TELEMETRY=true -- <cesta k blender-mcp.exe>`
- **safe mode vypnut 2026-09-15** (`BLENDER_MCP_SAFE_MODE` na `"0"` v `~/.claude.json`).
  Důvod: safe mode blokuje `open()`/`exec()`, takže Blender si nemohl načíst
  `blender/build_trailer.py` z disku a celý skript se musel posílat přes MCP při každé
  iteraci — drahé a hrozilo rozejití souboru a scény. Nově stačí
  `exec(open(cesta).read())`. Parser bere jako zapnuto jen `true/1/yes/on`.
  Změna se projeví až po restartu sezení (server dědí env při startu).
- addon: `C:\Users\Pavel\AppData\Roaming\Blender Foundation\Blender\4.3\scripts\addons\blender_mcp_addon.py`
  (verze 1.7, protokol 7 — sedí s `EXPECTED_ADDON_PROTOCOL_VERSION` serveru), zapnutý,
  preference uložené
- ovládání v Blenderu: **View3D > Sidebar (N) > MCP for Blender**

**Gotcha:** Blender 4.3 sice `scripts/addons` v instalačním adresáři vypisuje jako addon dir,
ale addon odtud **nenačte** (nová struktura s `addons_core`). Musí jít do uživatelské cesty
pod `%APPDATA%`, i u portable instalace.

**Telemetrie:** balíček ji má zapnutou a posílá přes `httpx`. Vypnuta přes
`BLENDER_MCP_DISABLE_TELEMETRY=true` (uznává i `DISABLE_TELEMETRY` a `MCP_DISABLE_TELEMETRY`).

**Provoz:** Blender musí běžet **s GUI** (headless nefunguje), jen jedno připojení naráz.
V safe mode jsou zablokované souborové a síťové operace ve skriptech.

**Jak to používat:** Pavel Blender neumí, takže MCP je „ukaž mi, jak se to dělá", ne „udělej to
za mě" — bez znalosti Blenderu nejde zkontrolovat, co MCP provedl (špatný scale, převrácené
normály, nezaaplikované transformace se projeví až při exportu nebo ve hře). Ukládat před každou
větší operací. Pro vlek se stejně počítá s parametrickým `bpy` skriptem do souboru
(opakovatelný), MCP na doladění a kontrolu.

**Blockout hotov (2026-09-15):** parametrický skript `blender/build_trailer.py`, aktuální
stav `blender/spraydrone_trailer.blend`, schválený základ uložen jako
`blender/spraydrone_trailer_base.blend`. Gooseneck rám, tandem náprava, 2× IBC nádrž
a 2× elektrocentrála na ose, zvýšená plošina (stejná půdorysná velikost jako ložná plocha)
na sloupcích s křížovými vzpěrami, nízké zábradlí z tyček s průchodem u žebříku. Bez stříšky.

### 1. Vlek, který se rozloží a zamkne

Žádný dron, žádný postřik. Přijedu, odpojím, rozložím plachtu, vlek se zamkne, složím, odjedu.

Celé je to Blender + XML + minimum Lua a je to samo o sobě dohratelná věc. Zároveň to provede
celým řetězem Blender → `.i3d` → GIANTS Editor → `modDesc.xml` → hra — kdyby se řetěz zadrhl,
zjistí se to po týdnu, ne po třech měsících.

Tohle nahrazuje budovu z fotogrammetrie jako **první blenderové cvičení** (viz
`E:\ClaudeProjects\FS25-Mapping\PRVNI-BUDOVA.md`): hranatá technika, žádný RealityScan,
žádné retopo, žádný scan cleanup.

### 2. Dron: základní cyklus

Vzlet, let na bod, přistání, výměna baterky a dočerpání na vleku. Pořád bez postřiku
a bez generátoru — jen ať ten cyklus spolehlivě běhá dokola.

### 3. Generátor linek + postřik + dávkování

Tady je skutečná práce.

### 4. Ovládací plošina s mapou

Až nakonec. Do té doby stačí výběr pole tím, že stojíš na něm.

## Otevřené otázky (rozhodují o designu, řešit před etapou 0/1)

1. ~~**Přesná verze Blenderu**, kterou snese GIANTS exporter 10.0.2 i `blender-i3d-importer`
   zároveň.~~ **Vyřešeno 2026-09-15: nejdou dohromady.** Podle GDN fóra (David Zadnik, GIANTS)
   exporter řady 10 vyžaduje **Blender 4.2 nebo 4.3** a s 4.4 ani 4.5 nefunguje;
   `blender-i3d-importer` chce naopak 5.1+. → **Zvolen Blender 4.3.1, importer škrtnut** —
   stavíme od nuly, cizí `.i3d` importovat nepotřebujeme a na nahlédnutí do base-game modelu
   je GIANTS Editor. Kdyby byl importer někdy potřeba, portable ZIPy jdou mít vedle sebe.
   Zdroj: https://gdn.giants-software.com/thread.php?categoryId=8&threadId=15969
2. **Jak base game technicky zamyká rozložený stroj na místě** — najít existující precedent
   v `$data`, ne si vymýšlet vlastní řešení. Rozhoduje to, jestli vlek bude `vehicle`
   s animací a zamrzlou fyzikou, nebo něco jiného. Zpětně se to mění špatně.

## Blender MCP (stav k 2026-09)

Existuje ve dvou podobách:

- **oficiální** (Blender Lab, jako Blender Extension) — https://www.blender.org/lab/mcp-server/ ,
  https://projects.blender.org/lab/blender_mcp — prototyp, těžiště v inspekci scény
  (polycount, materiály, přejmenování datablocků), ne v tvorbě geometrie.
  **Vyžaduje Blender 5.1+ → pro nás nepoužitelný**, viz etapa 0
- **komunitní** https://github.com/ahujasid/blender-mcp (28,6k ★) — širší: create/modify/delete,
  materiály, libovolný Python, assety z Poly Haven/Sketchfab, export GLB/FBX;
  má `BLENDER_MCP_SAFE_MODE=1`

Obojí: addon v Blenderu otevře socket, MCP server do něj relayuje. Blender musí běžet s GUI,
jen jedno připojení naráz.

**Pro tenhle projekt to není zlom.** Modely jsou hranatá technika → parametrický `bpy` skript
do souboru spuštěný přes `blender --python` je lepší než MCP (opakovatelný, verzovatelný,
změna parametru = přegenerování). MCP se hodí na interaktivní doladění a kontrolu scény.
Export do `.i3d` MCP neřeší vůbec — to dělá GIANTS exporter addon mimo MCP.

Navazuje na závěry v `E:\ClaudeProjects\FS25-Mapping\LLM-AUTOMATIZACE.md`.

## Zdroje

- AeroSpray: https://www.kingmods.net/en/fs25/mods/81272/agro-drone-aerospray-s70l ,
  https://www.fs25modhub.com/agro-drone-aerospray-s70l-v1-1-0-1 , https://level55.itch.io
- Courseplay FS25: https://github.com/Courseplay/Courseplay_FS25
- Reálná předloha: DJI Agras + servisní přívěs, DJI D-RTK 3 mobilní stanice
