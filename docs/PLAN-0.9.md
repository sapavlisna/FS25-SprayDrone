# Plán 0.9.0.0 — vlek zvlášť, tři velikosti dronu, dokupování baterií

Navazuje na 0.8 (`docs/PLAN-0.8.md` → Stav).

## Stav (2026-09-28, B3 + L4 hotové, test T společně s 0.8)

- **Ověřeno ve hře**: obchod — volby Dron (bez / S / M / L) a Baterie 0–5 s cenami (+7 000 / 12 000 / 22 000 €,
  1 500 €/ks), náhled dronu i prázdného heliportu se mění podle volby, registrace konfigurací bez varování schématu.
  Dílna „Přizpůsobit“ u prodejce: M/3 → S/2 a S/2 → L/5, nabití baterií se přeneslo jako podíl, nové plné.
  Let, postřik (2 / 4 / 2 kužely), zvuk (výška v logu 1,25 u S), hadice k hrdlu S, výdrž a odhady všech tří variant;
  L s 5 bateriemi v noci na poli 2, uložení a načtení (`battery(i)#level`, konfigurace). Vlek bez dronu: prázdný
  heliport, bez úchytů, F1, `Alt+7` hláška, nabíjení 2 baterií, přečerpání do IBC.
- **Úklid po B3 a L4**: fallbacky na `droneRoot`, `droneClamp*`, `batterySlotDrone` smazané (Station, Service, test 7
  v `test_l4.lua`, test 8 teď ověřuje vygenerovaný XML); trysky S a L v šabloně podle modelu (z −0,657 / −0,823).
- **Neověřeno**: 0 baterií ve hře (běh přerušen zavřením hry zvenku; offline test prochází), hadice u L zblízka,
  zvuk poslechem, MP. Obrázek do obchodu je starý (headless nepřekresluje; jde jen v GUI Blenderu).
- Zjištění: vanilla dílna účtuje plnou cenu nově zvolených voleb (ne rozdíl) a vlek po změně vytvoří odpojený.

## Rozhodnutí Pavla (2026-09-28)

- Nákup přes **konfigurace vleku** v obchodě: *Dron* = žádný / malý / střední / velký, *Baterie* = 0–5 ks.
  Dokoupení / výměna později v dílně („Přizpůsobit“, platí se rozdíl) — vanilla chování konfigurací.
- Velikosti **podle DJI Agras**, každá vlastní model a parametry.

## Parametry variant (zdroj: ag.dji.com/t25/specs, t50, t100/specs)

| | malý „S“ (T25) | střední „M“ (T50, dnešní) | velký „L“ (T100) |
|---|---|---|---|
| nádrž | 20 l | 40 l | 100 l (hra: 75 l, ať to baterie unese — rozhodne L proud podle modelu baterie) |
| záběr | 4–7 m → **6 m** | **9 m** | 5–13 m → **11 m** |
| hmotnost bez baterie | 25,4 kg | 39,9 kg | 75 kg |
| baterie | DB800: 15,5 Ah × 52,22 V = 0,81 kWh, 6,6 kg | DB1560: 1,567 kWh, 12,1 kg | DB2160: 41 Ah × 52 V = 2,13 kWh, 14,7 kg |
| nabití | 9–12 min | 9–12 min (30→95 % 10 min) | 30→95 % 8–9 min |
| rozměry složený | 1050 × 690 × 820 mm | dnešní model | 1105 × 1265 × 975 mm |
| rozložený (s vrtulemi) | 2585 × 2675 mm | dnešní model | 3220 × 3224 mm |
| vrtule | 4× 50″ (jednoduché, ne souosé), Ø 1,27 m | 4 ramena × 2 souosé | 4 ramena × 2 souosé 62″ |
| trysky | 2 zadní (rozteč 1368 mm) | dnešní | 2 na ramenu postřiku (rozteč 1834 mm) |

Výdrž (`batteryMinutes` s plnou nádrží) u S a L odvodit tak, aby model spotřeby (kvadrát hmotnosti) dal podobný
čas jako T50 (~7–8 min s plnou nádrží); odůvodnit v poznámce. Ceny orientačně: vlek bez dronu ~8 500 €, dron
S ~9 000 €, M ~15 000 €, L ~28 000 €, baterie za kus podle varianty nejde (konfigurace má pevnou cenu) → 1 500 €/ks.

## Kontrakt uzlů (proud B3 vyrábí, L4 používá)

Každý dron má **prefix** `Drone_S_`, `Drone_A_` (M, dnešní) nebo `Drone_L_` a stejné přípony:
`Root` (kořen, dnešní `droneRoot` se přejmenuje na `Drone_A_Root`), `Tilt`, `ArmPivot_i`, `Rotor_*`, `Blade_*`,
`Led_i`, `LedLight_i`, `FillPort`, `BatterySlot` (dnešní `batterySlotDrone` → `Drone_A_BatterySlot`) a úchyty lyžin
`Clamp_i` + závěsy `ClampHinge_i` (dnešní `droneClamp*` / `droneClampHinge_*` → `Drone_A_Clamp_i` / `Drone_A_ClampHinge_i`).
Všechny tři drony jsou v i3d na plošině (střed heliportu), viditelnost řídí konfigurace (`objectChange` na `Root` a úchyty).
Baterie: `battery1..5` zůstávají jako kořeny (sloty se nemění), pod každým tři meshe `battery<i>S`, `battery<i>M`,
`battery<i>L`; skript ukáže ten podle varianty. Šachty nabíječky a držák u centrály musí pojmout největší (DB2160).

Export generuje v šabloně `{{DRONE_PARTS_S}}`, `{{DRONE_PARTS_M}}`, `{{DRONE_PARTS_L}}` (tilt, foldPart, rotor, …
jako dnes `{{DRONE_PARTS}}`) a `{{CLAMP_PARTS}}` pro úchyty všech tří. Strukturu `<sprayDrone>` s bloky variant
(`<drone name="S" prefix="Drone_S_" … parametry …>{{DRONE_PARTS_S}}</drone>` …) píše L4 v šabloně; B3 jen
dodá placeholdery a jejich obsah.

## Proudy

| proud | co | smí měnit |
|---|---|---|
| **B3** Blender (headless) | modely S a L podle tabulky, přejmenování uzlů M, baterie tří velikostí, úchyty a heliport pro všechny tři, export placeholderů | `blender/*`, šablona mimo `<sprayDrone>` a mimo konfigurace |
| **L4** Lua | varianty v `<sprayDrone>`, konfigurace *Dron* (+ `objectChange`) a *Baterie* 0–5, režim bez dronu (žádné akce dronu, plánovač ohlásí „bez dronu“, ukazatele jen vlek, nabíjení baterií dál funguje), parametry a baterie podle varianty (kWh, hmotnost, nabíjení), zvuk (výška podle velikosti), efekt podle trysek, uložení/MP, `prepare_testsave.py --drone none|S|M|L` | `mod/.../scripts`, `modDesc.xml`, překlady, `<sprayDrone>` a bloky konfigurací v šabloně, `tools/prepare_testsave.py` |

Oba souběžně; sdílené soubory před úpravou znovu přečíst. Předávací poznámky `out/plan09/B3.md`, `out/plan09/L4.md`
(co ověřit ve hře a jak). Pak proud T: jeden společný test 0.8 + 0.9 (až budou povolena okna).
