# Rešerše: hadice a univerzální nádobka (2026-10-21)

Podklad pro přestavbu: vápnění bez konfigurace v obchodě (Max i Middle) a hadice, které nevypadají „divně“.
Stažené zdroje a skripty skenu: `tmp/reserse/`.

## Pumps N' Hoses Pack (FS25 DLC)

- Vydáno 8. 9. 2026 zdarma s patchem 1.23, vyvinulo Creative Mesh. Je to port DLC z FS22 a nevychází z Wopsterova Manure Systemu.
  - Zdroje: https://www.farming-simulator.com/dlc-detail.php?dlc_id=fs25pumpsnhoses, https://forum.giants-software.com/viewtopic.php?t=219364
- Soubor `pdlc_pumpsAndHosesPack.dlc` je šifrovaný. Dovnitř nevidí `gameSource.zip`, `sdk/xmlDoku` ani log.
- Ze hry jsou známá jména specializací (z cizích modů na GitHubu): `pdlc_pumpsAndHosesPack.umbilicalSprayer`, `bufferedSprayer`, `umbilicalReelOverload` a fillType `UMBILICAL_HOSE`.
- Veřejné API spojek pro modery neexistuje. Žádný mod nedeklaruje spojku kompatibilní s hadicemi DLC.
  - **Na DLC se nevázat.** Interní jména by se dala zjistit jen výpisem ve hře a byla by to křehká vazba.
- Hratelnost:
  - čerpadlo se postaví k jímce a zdroj pozná podle blízkosti,
  - naviják se při jízdě odvíjí,
  - úseky se spojují klíčem,
  - hadice se ucpává a čistí kompresorem.
- Čerpá jen kapaliny (kejda, digestát, voda), sypké nic.

## Vzory, které jdou číst

| zdroj | kde | co z něj |
|---|---|---|
| vanilla `ConnectionHoses.lua` | `E:\SteamLibrary\steamapps\common\Farming Simulator 25\sdk\debugger\gameSource.zip`, kopie v `tmp/reserse/gameSource/` | průvěs a vzhled hadice |
| Wopster Manure System (FS22, GPL-3) | github.com/stijnwop/manureSystem, `tmp/reserse/ms/` | hadice jako fyzikální vozidlo, spojky, ventil, MP |
| FS25_SlurryPipeSystem (Oscar Mods) | `E:\SteamLibrary\FS25-Mods\`, `tmp/reserse/FS25_SlurryPipeSystem/` | skinned hadice, ventil u IBC, raycast podlahy |
| LSFM Hose System (FS25) | https://fs25.net/lsfm-hose-system-v1-0/ | spojka na libovolnou nádrž (Alt+N), jen popis |

Wopster je pod GPL-3 a náš mod pod CC BY-NC-SA. Přebírat se smí principy, kód ne.

### Vanilla průvěs (`ConnectionHoses.lua:449`)

- Hadici vykresluje **jedna trubka deformovaná vertex shaderem** (`vehicleShader.xml`, varianta `localCatmullRom*`). Řídí ji 5 bodů a ani kostra, ani Lua na vrchol se nepoužívá:
  - `cv0` = start − `startStraightening` (hadice vychází ze spojky rovně),
  - `cv2` = střed startu a cíle, snížený o `max(L − d, 0.04·d) · centerPointDropFactor`,
  - `cv3` = cíl, `cv4` = cíl + `endStraightening` · směr spojky,
  - pak se střed zvedne, aby úhel ohybu neklesl pod `minCenterPointAngle` (výchozí 90°),
  - k tomu kmitání ze změny rychlosti nosné komponenty (`dampingFactor` 50, filtr 0,1/0,9).
- Parametry mají rozsah ±10, takže hadice smí sahat nejvýš 10 m od `hoseNode`.
- Klon trubky dá `g_connectionHoseManager:getClonedHoseNode(type, "DEFAULT", length, diameter)`.
- Jen jeden střední bod znamená jeden prověšený oblouk. Na hadici ležící po zemi přes nerovný terén to nestačí.

### Wopster (FS22)

- Hadice je samostatné vozidlo `flexibleHose`: 4 komponenty po 5 kg, 3 `componentJoint` s `rotLimit 22°`. Vzhled dává jedna shader trubka a střed se bere z prostředních komponent.
- Připojení vytvoří joint ke spojce (pružina 7500, tlumení 1500, breakable). Nesená hadice je joint na ruku hráče. Server ji odpojí, když vzdálenost přesáhne délku + 0,5 m.
- Spojka je `<manureSystemConnectors><connector type="COUPLING" node=… inRangeDistance="1.8" lockAnimationName=… manureFlowAnimationName=…/>`. Bez otevřeného ventilu se nečerpá.
- MP: stav (připojeno k vozidlu a spojce) jde ve streamu, akce eventy, fyziku simuluje server, tvar počítá klient.

### SlurryPipeSystem (FS25)

- Skinned mesh, 16 kostí na shape (postřikovač 32 kostí = dva shapes).
- Tvar je kubický Bézier: řídicí body odsazené po ose spojek o 0,4·rozpětí a snížené o 0,08·rozpětí. Konce hadice jsou `link()` na spojky.
- **Kosti drží nad terénem i nad raycastem dolů** (maska STATIC_OBJECT+TERRAIN+BUILDING+ROAD), takže hadice leží i na betonu. Vlastní kolize hadice mají vymazané bity podlahy, jinak kosti poskakovaly.
- Ovládání: ventil = rotační klíčové snímky pojmenovaného dílu. R krátce připojí nebo odpojí, podržení 0,8 s přepne ventil, směr jde měnit jen při zavřeném ventilu, otevřený ventil = čerpá.
- Vanilla IBC dostane spojku přesměrováním `loadSharedI3DFileAsync` na kopii i3d.
- MP: jen stavové eventy přes server, tvar si počítá každý klient.

## Proč je naše hadice mlýnku divná (`SprayDroneMill.lua` `groundedCurve`, `layoutChain`)

- Ostré zlomy: pád z oblouku na zem a spodek svislého stoupáku nemají zaoblení. Pod vstupem (asi 1,7 m vysoko) stojí rovná svislá „tyčka“.
- Délka se nedrží: vykreslená délka je délka dráhy a slack mění jen klikatění.
- Výška jen z terénu: hadice prochází koly a podvozkem a na betonu propadá.
- Konec křivky leží přímo v uzlu, bez přívodu, takže koncovka zajede do spojky.
- 72 tuhých článků s přesahem dělá mezery na vnější straně ohybů.
- Stav mlýnku se neukládá do savu.

Hadice dronu (`SprayDroneService.lua`) je na tom líp (pevná délka, Bézierův průvěs, přívod do hrdla), ale vykresluje se stejnými tuhými články.

## Co převzít

1. **Tvar:** tečny na koncích ve směru spojky (rovné konce 0,3–0,5 m), pevná délka, průvěs z přebytku délky `max(L − d, 0.04·d)`, žádný ohyb ostřejší než `minCenterPointAngle`. Úsek ležící na zemi držet nad terénem **a** nad raycastem podlahy.
2. **Vykreslení bez mezer:** buď vanilla shader trubka (krátké pevné propojení, jeden oblouk), nebo skinned mesh s kostmi (dlouhá hadice po zemi, víc shapes po 16 kostech).
3. **Spojka s ventilem:** uzel spojky s dosahem 1,5–1,8 m. R krátce připojí, podržení přepne ventil, animace páky jsou klíčové snímky. Čerpá se jen při připojené hadici, otevřeném ventilu a běžícím zdroji.
4. **Vápno hadicí** = stejný přenos l/s jako u kapaliny, rozdíl je jen kosmetický (zvuk kompresoru, prach, barva a průměr hadice).
5. **MP:** po síti jen stav (připojeno, ventil, nesená poloha), tvar počítá každý klient sám. Stav ukládat do savu.
