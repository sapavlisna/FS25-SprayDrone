"""Sestaví EDL (edl/<film>.json) a katalog.md z clips.json + clips_qc.json.

Spuštění: python tools/cinema/v2/edl_gen.py
Každý střih se ověří proti nejlepsi_okno kontroly, délkovým pravidlům a pohybové mapě.
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
V2 = os.path.join(ROOT, "tools", "cinema", "v2")
FPS = 60
XFADE = 0.5

CLIPS = json.load(open(os.path.join(V2, "clips.json"), encoding="utf-8"))
QC = json.load(open(os.path.join(V2, "clips_qc.json"), encoding="utf-8"))


def okna(q):
    w = q.get("nejlepsi_okno") or []
    if w and not isinstance(w[0], list):
        w = [w]
    return [list(map(float, x)) for x in w if x[1] > x[0]]


POSLEDNI = {}
for c in CLIPS:
    s = c.get("soubor")
    if not s or s not in QC:
        continue
    k = (c["akce"], c["kamera"])
    if k not in POSLEDNI or c["take"] > POSLEDNI[k]["take"]:
        POSLEDNI[k] = c

CHYBY = []
VAROVANI = []


def klip(akce, kam):
    c = POSLEDNI.get((akce, kam))
    if not c:
        raise SystemExit("neexistuje hodnocený klip %s %s" % (akce, kam))
    if QC[c["soubor"]]["stav"] == "vyrazeno":
        raise SystemExit("klip vyrazeno: %s" % c["soubor"])
    return c


def S(beat, zaber, akce, kam, a, b, typ, pohyb, smer="-", pozn="", prechod=None):
    c = klip(akce, kam)
    q = QC[c["soubor"]]
    if not any(w[0] - 1e-6 <= a and b <= w[1] + 1e-6 for w in okna(q)):
        CHYBY.append("%s %s%s [%s,%s] mimo nejlepsi_okno %s" % (zaber, akce, kam, a, b, okna(q)))
    if b > c["delka_s"] + 1e-6:
        CHYBY.append("%s přesahuje délku klipu" % zaber)
    d = b - a
    if typ == "D" and not 1.5 <= d <= 3.0:
        VAROVANI.append("%s detail %.1f s mimo 1,5–3 s" % (zaber, d))
    if typ in ("PC", "UI") and not 2.0 <= d <= 6.0:
        VAROVANI.append("%s záběr %.1f s mimo 2–6 s" % (zaber, d))
    if typ == "C" and not 2.0 <= d <= 8.0:
        VAROVANI.append("%s celek %.1f s mimo 2–8 s" % (zaber, d))
    return dict(beat=beat, zaber=zaber, akce=akce, kam=kam, a=a, b=b, typ=typ, pohyb=pohyb, smer=smer,
                pozn=pozn, prechod=prechod, c=c)


# ---------------------------------------------------------------- střihy

MINI = [
    S("1-2", "mini-2.1", "mini-silnice", "B", 2.5, 8.5, "PC", "PAN", "L", "těsný průjezd, švenk po směru jízdy; mini-1.1 chybí (A, D vyřazeno), B/C jen PAN-L"),
    S("3", "mini-3.1", "mini-cesta", "D", 0.5, 5.0, "PC", "FOL", "-", "FOL zezadu přes pole; jediný použitelný klip, od 4 s cizí červený stroj v pozadí vpravo (použito do 5 s)"),
    S("3", "mini-3.2", "mini-dvur-prijezd", "D", 2.0, 7.0, "PC", "STAT", "-", "vyvýšený boční celek, souprava vjíždí a brzdí"),
    S("3", "mini-3.2", "mini-dvur-prijezd", "B", 7.5, 12.5, "PC", "PAN-sled", "R", "nízko, souprava zastavuje u sil, vlek čitelný"),
    S("4", "mini-4.1", "mini-rozlozeni", "A", 3.5, 7.5, "C", "ORB", "CW", "stěny se sklápí, panely se rozkládají (stěna ve vzduchu ~6 s je animace hry)"),
    S("4", "mini-4.1", "mini-rozlozeni", "B", 7.5, 10.5, "C", "ORB", "CCW", "oblet z opačné strany, dron se rozkládá na heliportu"),
    S("4", "mini-4.1", "mini-rozlozeni", "D", 10.5, 14.0, "C", "STAT", "-", "rozložený vlek před stodolou, dron stojí"),
    S("4", "mini-4.2", "mini-detaily", "A", 2.5, 5.5, "D", "NAJ", "-", "D1 plošina s heliportem a dronem"),
    S("4", "mini-4.3", "mini-detaily", "B", 8.5, 11.5, "D", "TILT-D", "-", "D2 elektrocentrála; výfuk jen částečně"),
    S("4", "mini-4.4", "mini-detaily", "A", 14.0, 17.0, "D", "STAT", "-", "D3 šachta baterií, otevřená"),
    S("4", "mini-4.5", "mini-detaily", "B", 20.0, 23.0, "D", "TRK", "R→L", "D4 nádrž 300 L, nádobka, mixér, čerpadlo"),
    S("4", "mini-4.6", "mini-detaily", "A", 25.5, 28.5, "D", "ODJ", "-", "D5 navíječ s modrou hadicí"),
    S("5", "mini-5.1", "mini-kanystr", "D", 1.5, 6.5, "PC", "NAJ", "-", "najetí na bednu, víko, oranžový kanystr HERBICID; kanystry v bedně jsou zelené (nesoulad barvy)"),
    S("5", "mini-5.2", "mini-kanystr", "A", 10.5, 15.0, "PC", "PAN", "R", "kanystr nad hrdlem nádobky, štítek čitelný ~11–14 s; střih před odletem kanystru (Z9)"),
    S("6", "mini-6.1", "mini-planovac", "B", 1.5, 5.0, "UI", "NAJ", "-", "najetí na tablet; rozsvícení displeje se nepozná (modrá obrazovka s logem)"),
    S("6", "mini-6.2", "mini-planovac", "A", 7.0, 13.0, "UI", "MAPA+", "-", "mapa, přiblížení na pole 4; v kartě červená varování (Z5), ikony vozidel"),
    S("6", "mini-6.3", "mini-planovac", "B", 23.0, 28.0, "UI", "STAT", "-", "karta pole 4 / stránka MISE; červená varování o koncentrátu a přípravku (Z5)"),
    S("7", "mini-7.1", "mini-let", "A", 3.0, 9.0, "C", "JIB-U", "-", "vzlet dronu z heliportu, jeřáb nahoru"),
    S("7", "mini-7.2", "mini-let", "C", 15.5, 21.0, "PC", "FOL", "čelo", "nejlepší 7.2: dron s bílou mlhou zepředu 3/4; mlha bílá, ne bílomodrá"),
    S("7", "mini-7.3", "mini-let", "B", 22.5, 27.5, "C", "TOP", "-", "svisle shora, úzká stopa mlhy po řádcích"),
    S("7", "mini-7.4", "mini-let", "A", 30.0, 33.5, "PC", "TRK", "R→L", "boční tracking, dron s mlhou nízko; po 34 s dron za stromy (nepoužito)"),
    S("7", "mini-7.5", "mini-navrat-servis", "D", 1.5, 5.0, "PC", "STAT", "-", "dron přilétá zespodu"),
    S("7", "mini-7.5", "mini-navrat-servis", "C", 5.0, 7.5, "PC", "FOL", "-", "FOL shora zezadu, dron klesá a přistává na heliport"),
    S("7", "mini-7.6", "mini-navrat-servis", "A", 9.5, 14.5, "PC", "ORB", "CCW", "oblet kolem dronu na desce, hadice napojená; výměna baterie a doplnění se nečtou"),
    S("7", "mini-7.7", "mini-navrat-servis", "B", 15.0, 18.5, "PC", "NAJ", "-", "detail dronu s hadicí; baterie ani truhla v záběru nejsou (výměnu nutno dotočit)"),
    S("8", "mini-8.1", "mini-slozeni-odjezd", "A", 2.5, 7.0, "C", "JIB-D", "-", "dron skládá ramena, jeřáb dolů"),
    S("8", "mini-8.1", "mini-slozeni-odjezd", "B", 8.0, 12.0, "C", "ORB", "CCW", "plošina se sklápí, bedna se zavírá (stěna ve vzduchu ~11 s je animace)"),
    S("8", "mini-8.2", "mini-slozeni-odjezd", "C", 16.0, 20.0, "PC", "FOL", "-", "FOL za soupravou po štěrku; od 20 s ikony hotspotů a kráva (nepoužito)"),
    S("8", "mini-8.2", "mini-slozeni-odjezd", "A", 20.0, 26.5, "C", "STAT", "-", "tele zezadu, odjezd soupravy; závěr filmu"),
]

MIDDLE = [
    S("1-2", "middle-1.1", "middle-silnice", "D", 1.5, 5.0, "C", "STAT", "-", "tele nízko ze svahu, souprava sjíždí na kameru"),
    S("1-2", "middle-2.1", "middle-silnice", "B", 2.0, 6.5, "PC", "PAN", "L", "těsný průjezd, švenk po směru jízdy; konec před zmenšením do dálky"),
    S("1-2", "middle-2.1", "middle-silnice", "A", 7.0, 9.0, "PC", "STAT", "-", "těsný průjezd, vlek ořezaný levým okrajem (záměrně); otočení za vozidlem (3/4 zezadu) chybí"),
    S("3", "middle-3.1", "middle-cesta", "A", 1.0, 5.5, "PC", "TRK", "R→L", "nízký boční tracking, souprava jede přes louku (podle QC zleva doprava v obraze)"),
    S("3", "middle-3.1", "middle-cesta", "D", 6.0, 10.0, "PC", "FOL", "-", "FOL zezadu, pickup skrytý za vlekem"),
    S("3", "middle-3.2", "middle-polo-prijezd", "D", 0.5, 5.5, "C", "NAJ-zoom", "-", "vyvýšený široký záběr, voda a rákos v pozadí, pomalé přiblížení; souprava malá"),
    S("3", "middle-3.2", "middle-polo-prijezd", "B", 6.5, 10.5, "PC", "STAT", "-", "souprava stojí na louce; lehce listí vlevo dole, voda v pozadí není vidět"),
    S("4", "middle-4.1", "middle-rozlozeni", "A", 2.5, 6.5, "C", "ORB", "CCW", "rozvinutí plachet, sklopení žebříku, stožár; pickup vpravo částečně v keři"),
    S("4", "middle-4.1", "middle-rozlozeni", "D", 6.5, 9.5, "PC", "TRK", "R→L", "boční jízda, plachty, žebřík a stožár čitelné"),
    S("4", "middle-4.1", "middle-rozlozeni", "C", 9.5, 12.5, "C", "STAT", "-", "vyvýšený boční celek rozloženého vleku; rákos v rohu"),
    S("4", "middle-4.2", "middle-detaily", "B", 1.5, 4.5, "D", "NAJ", "-", "D1 žebřík s příčkami"),
    S("4", "middle-4.3", "middle-detaily", "A", 7.6, 10.6, "D", "TRK", "L→R", "D2 kolejnice plachty, nádrž 1000 L"),
    S("4", "middle-4.4", "middle-detaily", "B", 15.0, 18.0, "D", "STAT", "-", "D3 truhla nabíječek a heliport shora; sloty vidět jen shora"),
    S("4", "middle-4.5", "middle-detaily", "B", 20.0, 23.0, "D", "NAJ", "-", "D4 nádrž 1000 L, čerpadlo, nádobka"),
    S("4", "middle-4.6", "middle-detaily", "A", 25.5, 28.5, "D", "JIB-U", "-", "D5 stožár s anténou a GPS"),
    S("5", "middle-5.1", "middle-kanystr", "A", 3.5, 8.0, "PC", "NAJ", "-", "roleta nahoru, police s kanystry, štítky 20 l čitelné"),
    S("5", "middle-5.2", "middle-kanystr", "C", 10.0, 14.5, "PC", "STAT", "-", "kanystr HNOJIVO nad nádobkou, štítek čitelný 10–13 s; kanystr visí bez opory (Z9, animace hry)"),
    S("6", "middle-6.2", "middle-planovac", "A", 7.0, 12.0, "UI", "MAPA-", "-", "mapa s polem 91, oddálení; červená varování v kartě (Z5); middle-6.1 chybí (kamera v listí)"),
    S("6", "middle-6.3", "middle-planovac", "B", 24.0, 29.0, "UI", "STAT", "-", "stránka MISE s kartou pole; ikony cizích vozidel nahoře (Z5)"),
    S("7", "middle-7.0", "middle-let", "A", 1.0, 4.0, "D", "NAJ", "-", "detail dronu M na heliportu, štítek BZ-M"),
    S("7", "middle-7.1", "middle-let", "C", 9.0, 13.0, "C", "JIB-U", "-", "vzlet nad vodou za vlekem, voda a domek"),
    S("7", "middle-7.1", "middle-let", "B", 13.5, 17.5, "C", "STAT", "-", "kamera zespodu proti obloze, dron odlétá nad vlek s anténou"),
    S("7", "middle-7.2", "middle-let", "A", 49.0, 54.5, "PC", "FOL", "-", "FOL zepředu shora, žlutozelená mlha nad polem (čekací smyčka 17–47 s vynechána)"),
    S("7", "middle-7.3", "middle-let", "B", 58.5, 62.5, "C", "TOP", "-", "svisle shora, úzká stopa po řádcích"),
    S("7", "middle-7.4", "middle-let", "C", 64.5, 68.5, "PC", "TRK", "L→R", "nízko přes cestu a pole, dron s mlhou přelétá; externí pohled, ne z palubní kamery"),
    S("7", "middle-7.5", "middle-navrat-servis", "B", 2.5, 5.5, "PC", "STAT", "-", "vyvýšená statika, dron přilétá a sestupuje"),
    S("7", "middle-7.5", "middle-navrat-servis", "C", 5.5, 8.0, "PC", "FOL", "-", "FOL za dronem, snáší se na plošinu, voda a rákos v pozadí"),
    S("7", "middle-7.7", "middle-navrat-servis", "B", 9.0, 12.0, "D", "NAJ", "-", "jediný záběr s výměnou baterie; vybitá baterie vylétá ze slotu (Z9, animace hry)"),
    S("7", "middle-7.6", "middle-navrat-servis", "C", 13.0, 17.5, "PC", "ORB", "CCW", "oblet z výšky kolem dronu na heliportu, hadice napojená, voda v pozadí"),
    S("7", "middle-7.7", "middle-navrat-servis", "D", 17.5, 20.5, "D", "ODJ", "-", "detail dronu s hadicí a zeleným LED; baterie v záběru není"),
    S("8", "middle-8.1", "middle-slozeni-odjezd", "C", 3.5, 7.0, "C", "ORB", "CW", "oblet po levém boku: plachty se svinou, dron se skládá, stožár se zasouvá, žebřík se zvedá"),
    S("8", "middle-8.1", "middle-slozeni-odjezd", "A", 7.0, 11.0, "C", "ODJ", "-", "odjezd kamery od zavřeného vleku; keř vlevo okrajově"),
    S("8", "middle-8.2", "middle-slozeni-odjezd", "C", 16.0, 22.0, "C", "FOL", "-", "FOL zepředu shora na odjezd po louze; keře v dolní části od 17 s okrajově"),
]

MAX = [
    S("1-2", "max-1.1", "max-silnice", "D", 1.5, 5.5, "C", "STAT", "-", "tele nízko z krajnice, souprava sjíždí na kameru"),
    S("1-2", "max-2.1", "max-silnice", "B", 3.0, 7.5, "PC", "PAN", "L", "profil soupravy před stromy, švenk po směru jízdy; souprava dál od osy než plán"),
    S("3", "max-3.2", "max-zaparkovani", "D", 5.5, 11.5, "C", "STAT", "-", "vyvýšený boční záběr, souprava jede po pásu a zastaví; max-3.1 chybí"),
    S("4", "max-4.1", "max-rozlozeni", "A", 2.5, 6.5, "C", "ORB", "CW", "plachty se zdvihají, žebřík, stožár, drony na střeše"),
    S("4", "max-4.1", "max-rozlozeni", "B", 6.5, 9.5, "C", "ORB", "CCW", "oblet z druhé strany, BZUK čitelné"),
    S("4", "max-4.1", "max-rozlozeni", "D", 9.5, 12.5, "PC", "TRK", "R→L", "boční jízda, rozložený vlek s nádržemi 3000 L"),
    S("4", "max-4.2", "max-detaily", "B", 2.5, 5.5, "D", "NAJ", "-", "D1 žebřík zepředu"),
    S("4", "max-4.3", "max-detaily", "B", 8.5, 11.5, "D", "TRK", "R→L", "D2 vlek s plachtami a dronem v pohybu; A (jen dron a žebřík, listí v popředí) nahrazeno"),
    S("4", "max-4.4", "max-detaily", "B", 14.0, 17.0, "D", "STAT", "-", "D3 plošina s dronem shora; truhla a navíječe v záběru nejsou"),
    S("4", "max-4.5", "max-detaily", "B", 19.5, 22.5, "D", "NAJ", "-", "D4 nádrže a elektrocentrála"),
    S("4", "max-4.6", "max-detaily", "A", 25.5, 28.0, "D", "ODJ", "-", "D5 vodní ventily nádrží; vápnová spojka s kohoutem se nečte"),
    S("5m", "max-5m.1", "max-pumpa", "A", 1.0, 5.5, "C", "TRK", "R→L", "pumpa u zadku Maxu je ~2 % šířky, hadice (sání, výstup) nejsou vidět"),
    S("5m", "max-5m.2", "max-pumpa", "D", 8.0, 10.5, "D", "JIB-D", "-", "pan podél břehu, potok a rákos; sací koš v potoce a cedulky VSTUP/VÝSTUP nejsou vidět"),
    S("5m", "max-5m.3", "max-pumpa", "B", 12.0, 14.0, "D", "STAT", "-", "pevný rám s pumpou (malá, žlutočerná krabice); střih na shodu s 5m.4"),
    S("5m", "max-5m.4", "max-pumpa", "B", 14.5, 16.0, "D", "STAT", "-", "tentýž rám bez pumpy (schválená dvojice statik); zmizení je kvůli malé pumpě špatně čitelné"),
    S("5m", "max-5m.5", "max-mlynek", "A", 1.0, 5.5, "C", "ORB", "CCW", "oblet kolem mlýnku s Maxem v pozadí; hadice mlýnek→spojka není vidět", prechod="xfade %.1f" % XFADE),
    S("5m", "max-5m.6", "max-mlynek", "B", 9.0, 10.5, "D", "STAT", "-", "big bag stojí u mlýnku (poslední čistý okamžik před levitací)"),
    S("5m", "max-5m.6", "max-mlynek", "C", 16.0, 17.5, "D", "TILT-D", "-", "bílý proud vápna z big bagu do násypky; big bag dlouho levituje (11–15 s vynecháno)"),
    S("5m", "max-5m.7", "max-mlynek", "A", 18.5, 21.0, "D", "NAJ", "-", "detail motoru, šneku a spojky mlýnku; prstenec nesvítí"),
    S("5m", "max-5m.8", "max-mlynek", "B", 23.0, 28.5, "C", "ORB", "CW", "oblet mlýnku s okrajem Maxu; hadice do Maxu a svítící prstenec nejsou vidět"),
    S("6", "max-6.1", "max-planovac", "B", 2.0, 5.5, "UI", "NAJ", "-", "najetí na displej plánovače, od ~4 s velký a čitelný"),
    S("6", "max-6.2", "max-planovac", "A", 8.5, 14.0, "UI", "MAPA+", "-", "mapa, výběr pole 59 → 60, přiblížení; ikony vozidel a cyan ikona (Z5)"),
    S("6", "max-6.3", "max-planovac", "B", 20.0, 24.0, "UI", "STAT", "-", "karta pole / stránka MISE; max-6.4 (letová plocha) chybí, v klipu je hotová a s červenou hláškou"),
    S("7", "max-7.0", "max-let", "B", 2.0, 5.0, "D", "NAJ", "-", "detail dronu 2 na plošině"),
    S("7", "max-7.1", "max-let", "A", 12.0, 17.5, "C", "JIB-U", "-", "vzlet obou dronů, odlétají nad pole (úvod 8–11 s kamera v rákosu vynechán)"),
    S("7", "max-7.2", "max-let", "C", 47.0, 51.5, "PC", "FOL", "čelo", "nejlepší 7.2: dva drony v bílé mlze na souběžných drahách, zepředu 3/4"),
    S("7", "max-7.4", "max-let", "B", 61.0, 65.0, "PC", "TRK", "L→R", "tracking jediného dronu nad zeleným polem, bez mlhy; strniště a Max v záběru nejsou; max-7.3 (TOP) chybí"),
    S("7", "max-7.5", "max-navrat-servis", "D", 3.5, 6.0, "PC", "STAT", "-", "záběr shora vpravo, dron přilétá"),
    S("7", "max-7.5", "max-navrat-servis", "C", 6.0, 8.5, "PC", "FOL", "-", "FOL za dronem nad rybníkem, přistání na přední plochu"),
    S("7", "max-7.6", "max-navrat-servis", "A", 10.0, 14.0, "PC", "ORB", "CCW", "oblet kolem dronu na desce, hadice, otevřená truhla, tahač"),
    S("7", "max-7.6", "max-navrat-servis", "C", 14.5, 18.5, "PC", "ORB", "CW", "oblet z opačné strany, druhý dron na zadní ploše"),
    S("7", "max-7.7", "max-navrat-servis", "D", 19.0, 22.0, "D", "ODJ", "-", "detail dronu s hadicí a baterií; výměna baterie do truhly není kompletně vidět"),
    S("8", "max-8.1", "max-slozeni-odjezd", "A", 2.0, 7.0, "C", "JIB-D", "-", "jeřáb zvysoka, drony se skládají, plachty se svinují"),
    S("8", "max-8.1", "max-slozeni-odjezd", "B", 9.0, 12.5, "C", "ORB", "CCW", "oblet po skládání (listí 3–8 s vynecháno)"),
    S("8", "max-8.2", "max-slozeni-odjezd", "C", 15.5, 19.0, "PC", "FOL", "-", "FOL za soupravou, odjezd po poli"),
    S("8", "max-8.2", "max-slozeni-odjezd", "A", 19.5, 25.5, "C", "STAT", "-", "tele zezadu, souprava odjíždí ke cestě; závěr filmu"),
]

SPOL = [
    S("epilog", "spol-1", "spol", "A", 6.5, 13.0, "C", "NAJ", "-", "tři soupravy před stodolou, drony krouží; vleky malé; vlevo na dvoře leží kanystry a pytel z prod (Z2)"),
    S("epilog", "spol-2", "spol", "A", 14.0, 20.0, "PC", "TRK", "L→R", "boční jízda podél řady, soupravy jen jako malé siluety; kanystry a pytel vlevo (Z2)"),
    S("epilog", "spol-3", "spol", "A", 24.5, 31.0, "C", "JIB-U", "-", "jeřáb nahoru k pohledu na tři soupravy; drony už nejsou v záběru, soupravy malé"),
    S("epilog", "spol-3", "spol", "B", 31.0, 35.0, "C", "ORB", "CW", "pohled shora na tři soupravy a drony; krávy na pastvině (Z3) a cizí pytel u okraje (Z2)"),
]

PROD = [
    S("prod-1", "prod-1", "prod-vleky", "A", 1.5, 6.5, "C", "NAJ", "-", "celek řady před stodolou; vleky v pozadí jen drobné tmavé siluety, drony S/M/L nerozlišitelné"),
    S("prod-2", "prod-2", "prod-rada", "A", 2.0, 7.5, "PC", "TRK", "L→R", "kanystry po ~3 s statiky; čelní strana hladká bez štítku (HNOJIVO/HERBICID/nafta se nepřečtou, jen barva)"),
    S("prod-2", "prod-2", "prod-rada", "B", 7.5, 12.0, "PC", "TRK", "R→L", "kanystry z druhé strany, opačné pořadí; štítky nečitelné"),
    S("prod-2", "prod-2", "prod-rada", "A", 12.0, 15.5, "PC", "TRK", "L→R", "pytel vápna zboku zezadu, nápis VÁPNO vzhůru nohama a dole ořezaný"),
    S("prod-3", "prod-3", "prod-rada", "A", 17.5, 21.5, "PC", "TILT-U", "-", "big bag s CaCO3 štítkem čitelný, k poutkům"),
    S("prod-4", "prod-4", "prod-rada", "A", 24.0, 29.5, "PC", "TRK", "R→L", "násypka a pumpa, barvy spojek vidět; texty VSTUP/VÝSTUP/VÁPNO nečitelné"),
    S("prod-4", "prod-4", "prod-rada", "B", 29.5, 33.0, "PC", "TRK", "L→R", "pumpa a násypka z druhé strany; texty nečitelné"),
    S("prod-5", "prod-5", "prod-rada", "A", 33.5, 39.5, "PC", "ORB", "CW", "reléová tyč s teleskopem, zelený LED jen drobný bod"),
    S("prod-6", "prod-6", "prod-vleky", "A", 9.0, 12.0, "D", "NAJ", "-", "otevřená truhla nabíječek vleku v pozadí; baterie ve slotech nejsou jasně vidět"),
    S("prod-8", "prod-8", "prod-rada", "A", 41.0, 46.5, "C", "ODJ", "-", "závěrečný celek řady; kanystry drobné; prod-7 (tři vleky s drony S, M, L) chybí"),
]

FILMY = {
    "mini": dict(strihy=MINI, cil=140, text="mini (Mini, herbicid, 1 dron S)"),
    "middle": dict(strihy=MIDDLE, cil=145, text="middle (Middle, hnojivo, 1 dron M)"),
    "max": dict(strihy=MAX, cil=170, text="max (Max, vápno, 2 drony)"),
    "spol": dict(strihy=SPOL, cil=25, text="spol (epilog, tři vleky)"),
    "prod": dict(strihy=PROD, cil=55, text="prod (produktová scéna)"),
}

SLABA = {
    "mini": [
        "mini-1.1 chybí: silnice A a D vyřazeny (keř, značka), B a C jsou PAN-L z jižní strany",
        "mini-3.1: jediný použitelný klip je cesta D (FOL), od 4 s cizí červený stroj; cesta A, B, C vyřazeny",
        "mini-5.x: kanystry v bedně jsou zelené, kanystr herbicidu oranžový (nesoulad)",
        "mini-6.x: v kartě pole červená varování o koncentrátu a přípravku (Z5); displej se vizuálně nerozsvěcuje",
        "mini-7.6/7.7: doplnění nádrže a výměna baterie se nečtou, plovoucí baterie (Z9) vynechána",
        "mini-7.2: mlha je bílá, ne bílomodrá",
    ],
    "middle": [
        "middle-6.1 chybí (obě kamery v listí); 6.x má červená varování a ikony cizích vozidel (Z5)",
        "middle-2.1: otočení za vozidlem do 3/4 zezadu je jen v PAN-L kamery B, A/D jsou statické",
        "middle-3.2: souprava malá, voda jen v kameře D; B bez vody a s listím",
        "middle-5.2: kanystr visí bez opory (animace hry, Z9)",
        "middle-7.4: externí pohled, ne z palubní kamery dronu",
        "middle-7.6/7.7: výměna baterie vidět jen v jednom záběru (B, 9–12 s) a s plovoucí baterií (Z9)",
        "middle-8.2: použitelný jen klip C, ostatní kamery zakryté keři",
    ],
    "max": [
        "max-3.1 chybí (akce bez pokrytí)",
        "max-4.3 a 4.4: plachty/kolejnice a truhla s navíječi v záběrech chybí (A slabší, B shora na plošinu)",
        "max-5m.1–5m.4 (pumpa): pumpa ~2–5 % šířky, hadice a cedulky nejsou vidět, zmizení pumpy špatně čitelné",
        "max-5m.5–5m.8 (mlýnek): hadice mlýnek→spojka a svítící prstenec nikde vidět, big bag levituje (Z9), zvednutí/vyklopení chybí",
        "max-6.4 (letová plocha) chybí: v klipu je hotová a s červenou hláškou",
        "max-7.3 (TOP) chybí: stopa vápna shora není vidět",
        "max-7.4: jeden dron, bez mlhy, ne strniště, Max nevidět",
    ],
    "spol": [
        "všechny záběry slabé: soupravy malé, vlevo kanystry a pytel z prod (Z2), v B krávy (Z3)",
        "drony ve vzduchu jen v prvním záběru (spol-1)",
    ],
    "prod": [
        "štítky kanystrů (hladká čelní strana), pumpy a násypky nečitelné; pytel vzhůru nohama a ořezaný",
        "prod-7 (tři vleky s drony S, M, L) chybí: klip prod-vleky má jen A t1, v použitelném okně jen prod-1 a prod-6",
        "prod-6: baterie v truhle nejsou jasně vidět",
    ],
}


def spocti(strihy):
    frames = 0
    dl = []
    for i, s in enumerate(strihy):
        n = round((s["b"] - s["a"]) * FPS)
        dl.append(n)
        if i == 0 or not (s["prechod"] or "").startswith("xfade"):
            frames += n
        else:
            frames += n - round(XFADE * FPS)
    return frames / FPS


def kontrola_pohybu(film, strihy):
    zpravy = []
    for p, n in zip(strihy, strihy[1:]):
        if p["pohyb"] == n["pohyb"] and p["smer"] == n["smer"]:
            zpravy.append("%s: %s po %s stejný pohyb %s %s" % (film, n["zaber"], p["zaber"], n["pohyb"], n["smer"]))
    return zpravy


def zapis_edl(film, cfg):
    st = cfg["strihy"]
    prev = None
    for s in st:
        if s["prechod"] is None:
            s["prechod"] = "xfade %.1f" % XFADE if prev is not None and film in ("mini", "middle", "max") and s["beat"] != prev["beat"] else "cut"
        prev = s
    delka = spocti(st)
    hlavicka = dict(
        film=film,
        popis=cfg["text"],
        verze=1,
        fps=FPS,
        rozliseni="1920x1080",
        celkova_delka_s=round(delka, 2),
        cilova_delka_s=cfg["cil"],
        pocet_strihu=len(st),
        pravidlo_klipu="poslední hodnocený take akce × kamery, nikdy vyrazeno; in/out vždy uvnitř nejlepsi_okno",
        slaba_mista=SLABA[film],
    )
    seznam = []
    for s in st:
        c = s["c"]
        seznam.append(dict(
            beat=s["beat"], zaber=s["zaber"], klip=c["soubor"], kamera=s["kam"], take=c["take"],
            stav=QC[c["soubor"]]["stav"], in_s=s["a"], out_s=s["b"], delka_s=round(s["b"] - s["a"], 2),
            prechod=s["prechod"], typ=s["typ"], pohyb=s["pohyb"], smer=s["smer"], poznamka=s["pozn"],
        ))
    os.makedirs(os.path.join(V2, "edl"), exist_ok=True)
    with open(os.path.join(V2, "edl", film + ".json"), "w", encoding="utf-8") as f:
        json.dump(dict(hlavicka=hlavicka, strihy=seznam), f, ensure_ascii=False, indent=1)
    return delka


def escape(t):
    return (t or "").replace("|", "/").replace("\n", " ")


def beat_klic(vlek, b):
    poradi = ["1-2", "3", "4", "5", "5m", "6", "7", "8", "epilog", "prod"]
    return poradi.index(b) if b in poradi else 99


def katalog(pouzito):
    radky = ["# Katalog klipů SprayDrone v2", "",
             "Zdroj: `clips.json` + `clips_qc.json`. Sloupec Take má hvězdičku u posledního hodnoceného take akce × kamery (ten bere střih); "
             "`vyrazeno` se nepoužívá. Okno = `nejlepsi_okno` z kontroly (s). Použito = film: záběr v EDL.", ""]
    vleky = [("mini", "Mini"), ("middle", "Middle"), ("max", "Max"), ("mini+max+middle", "spol (epilog)"), ("prod", "prod")]
    for klic, nazev in vleky:
        zaznamy = [c for c in CLIPS if c["vlek"] == klic]
        zaznamy.sort(key=lambda c: (beat_klic(klic, c["beat"]), c["akce"], c["kamera"], c["take"]))
        radky += ["## %s" % nazev, "",
                  "| beat | záběry | soubor | kam | take | délka s | stav | nejlepší okno | poznámka | použito |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for c in zaznamy:
            s = c.get("soubor")
            q = QC.get(s) if s else None
            if q:
                stav = q["stav"]
                okno = ", ".join("%g–%g" % tuple(w) for w in okna(q)) or "–"
                pozn = " ".join(q["nalezy"][:2])
                if len(pozn) > 230:
                    pozn = pozn[:227] + "…"
                nazev_s = os.path.basename(s)
                delka = "%.1f" % c["delka_s"]
            else:
                stav = "chyba natáčení" if c["stav"] == "chyba" else c["stav"]
                okno = "–"
                pozn = "bez souboru (záznam o neúspěšném natočení)" if not s else "bez hodnocení"
                nazev_s = os.path.basename(s) if s else "(žádný soubor)"
                delka = "–" if c.get("delka_s") is None else "%.1f" % c["delka_s"]
            posl = "*" if s and POSLEDNI.get((c["akce"], c["kamera"])) is c else ""
            pz = pouzito.get(s, []) if s else []
            radky.append("| %s | %s | %s | %s | %s%s | %s | %s | %s | %s | %s |" % (
                c["beat"], ", ".join(z.split("-", 1)[1] for z in (c.get("zabery") or [])), nazev_s, c["kamera"], c["take"], posl, delka,
                stav, okno, escape(pozn), "; ".join(pz) or "–"))
        radky.append("")
    with open(os.path.join(V2, "katalog.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(radky))


def main():
    pouzito = {}
    for film, cfg in FILMY.items():
        for s in cfg["strihy"]:
            pouzito.setdefault(s["c"]["soubor"], []).append("%s: %s" % (film, s["zaber"]))
    for film, cfg in FILMY.items():
        d = zapis_edl(film, cfg)
        n = len(cfg["strihy"])
        print("%-7s střihů %2d  délka %.1f s (cíl %d)" % (film, n, d, cfg["cil"]))
        for z in kontrola_pohybu(film, cfg["strihy"]):
            VAROVANI.append(z)
    katalog(pouzito)
    for z in CHYBY:
        print("CHYBA:", z)
    for z in VAROVANI:
        print("varování:", z)
    if CHYBY:
        sys.exit(1)


if __name__ == "__main__":
    main()
