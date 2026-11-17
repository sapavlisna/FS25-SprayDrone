# Návrh: obrazovka plánovače ve stylu herní mapy (2026-10-23)

Pavel: „předělat obrazovku s mapou a ovládáním, aby to bylo hezčí a víc podobné tomu, jak to funguje u AD, PF a klasické mapy“.
Výchozí stav (commit 3af8327): mapa přes celou obrazovku, vpravo dlouhý textový panel kreslený `renderText` (desítky řádků,
nastavení jako řádky s − / +), vlevo nahoře lišta čipů vrstev skenu a tabulka přehledu polí, dole lišta tlačítek.

## Rešerše

**Herní mapa FS25** (`InGameMenuMapFrame`, snímek `out/mod_build/vanilla_mapa.png`):
- mapa přes celou plochu, vlevo tmavý panel (`fs25_subCategoryContainerBg`) přes celou výšku;
- nahoře v panelu přepínač stránek `< DRUHY PLODIN >` (`MultiTextOption` profil `fs25_subCategorySelector`) a pod ním tečky
  (`fs25_subCategorySelectorBox` s `RoundCorner fs25_subCategorySelectorDot`, `getIsSelected` podle stavu přepínače);
- pod ním seznam (`SmoothList fs25_mapList`), položka = barevný čtverec / ikona + VELKÝM písmem název, vybraná položka zeleně
  (#8BB20E, lineárně 0.258 0.445 0.004) se šipkou; sekce s nadpisy (`fs25_subCategoryListSectionHeader`);
- vpravo nahoře zaoblený box zůstatku (tmavý, popisek bílý, hodnota zeleně);
- dole černá lišta tlačítek s klávesami (`fs25_buttonBox`);
- úloha pomocníka se zakládá ve stejném levém panelu: nadpisy skupin `fs25_aiCreateJobParameterTitle` a volby
  `fs25_aiCreateJobMultiTextOption` v `BoxLayout fs25_aiCreateJobLayout` (vanilla `InGameMenuMapFrame`, Courseplay `CourseGeneratorFrame.xml`).

**Precision Farming**: mapy (dusík, pH, výnos, půda) jsou další položky přepínače herní mapy; legenda je seznam barevných
čtverců s popisem pod přepínačem. Vrstvu volí hráč v seznamu, žádná vlastní lišta čipů.

**AutoDrive** (`FS25_AutoDrive.zip`, rozbaleno jen GUI do `tmp/ad_ref`): nastavení jsou herní řádky
`fs25_multiTextOptionContainer` + `fs25_settingsMultiTextOption` + `fs25_settingsMultiTextOptionTitle` v `fs25_settingsLayout`
(stejně Courseplay); vlastní grafika jen pro HUD ve světě. Závěr: kde to jde, použít herní profily, ne vlastní kreslení.

## Nové rozložení

```
┌──────────────────────┬─────────────────────────────────────────────┬──────────────────────┐
│ [ikona] PLÁNOVAČ LETU│                                             │ PLÁN LETU            │
│ ◄   POLE   ►         │            mapa přes celou plochu           │ POLE 13              │
│   ● ○ ○ ○            │      (obrysy polí v dosahu, trasa, dosah,   │ Vlastní pole         │
│ V DOSAHU VLEKU       │       překryv skenu, ikony vleku a dronů)   │ ┌ varování / info ┐  │
│ ▣ Pole 13   vlastní  │                                             │ ┌────────┬────────┐  │
│   Plevel 25 % · …    │   ┌ bublina nad polem pod kurzorem ┐        │ │Dávky 3 │Čas 21 m│  │
│ ▣ Pole 12   zakázka  │                                             │ │Plocha  │Přípravek│ │
│ DALŠÍ VLASTNÍ POLE   │                                             │ │Nafta   │Baterie │  │
│ …                    │                                             │ │Přelet  │Vítr    │  │
│                      │                                             │ └────────┴────────┘  │
│                      │                                             │ PODLE SKENU 1712 l … │
│                      │                                             │ VLEK: nádrž, drony … │
├──────────────────────┴─────────────────────────────────────────────┴──────────────────────┤
│ [ESC] Zavřít  [↵] Spustit let  [X] Kreslit plochu  [Q] Snížit  [E] Zvýšit …               │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Levý panel** (herní prvky): záhlaví s ikonou a názvem, přepínač stránek s tečkami jako „Druhy plodin“:
  - **Pole**: `SmoothList` jako seznam pomocníků (ikona, název, štítek vlastní / zakázka, řádek stavu ze skenu nebo důvod, proč
    pole nejde); sekce „V dosahu vleku“ a „Další vlastní pole“; klik vybere pole a posune na něj mapu (nahrazuje tabulku přehledu);
  - **Mise** a **Let**: nastavení jako herní volby úlohy pomocníka (`fs25_aiCreateJobMultiTextOption`) po skupinách (Druh mise;
    Přelet, Pole, Drony) místo řádků s − / +; Q / E dál mění naposled vybranou volbu;
  - **Mapa skenu**: seznam `fs25_mapList` jako legenda herní mapy: sekce vrstev (klik = zvolit vrstvu, vybraná zeleně),
    barvy zvolené vrstvy a sekce „Trasa a dosah“ (barvy čar mapy, dřív dlouhý text legendy).
- **Karta plánu** vpravo (kreslená, ve stylu boxu zůstatku): štítek PLÁN LETU, název pole velkým písmem, druh; varování a
  informace jako barevné štítky s proužkem (červené = nejde letět, oranžové = pozor, zelené = hotovo, fialové = letová plocha);
  dlaždice 2 × N s bílými ikonami (`tools/make_ui_icons.py`) a hodnotami; zelený blok úspory podle skenu; dole stav vleku.
  Když se nevejde, stav vleku se zkrátí.
- **Mapa**: obrysy všech polí v dosahu (vlastní zeleně, zakázky zlatě, nepovolená šedě), vybrané silně zeleně, pod kurzorem
  bíle a vedle kurzoru bublina s názvem a důvodem; hlášky a návod kreslení jako pruh nahoře uprostřed mapy.
- **Dole** herní lišta tlačítek beze změny kláves; Snížit / Zvýšit vybrané jen na stránkách Mise a Let.
