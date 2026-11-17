"""Připraví zkušební uloženou hru (slot 11, kopie Pavlova Riverbend Springs ze slotu 5).

Do careerSavegame.xml přidá mód FS25_SprayDroneTrailer a do vehicles.xml pickup Lizard 2017
se zapřaženým vlekem vedle místa, kde se objeví hráč. Do missions.xml přidá dvě běžící zakázky farmy 1
v dosahu vleku: hnojení na poli 9 a herbicid na poli 8. Spustit opakovaně je bezpečné: předchozí
testovací vozidla, zakázky i záznam módu nejdřív odstraní.

python tools/prepare_testsave.py              vlek s tekutým hnojivem
python tools/prepare_testsave.py --herbicide  vlek s herbicidem
python tools/prepare_testsave.py --diesel 0.5 --batteries 25,40,30
                                              málo nafty, 3 baterie ve slotech vleku vybité (test čekání na nabití)
python tools/prepare_testsave.py --battery-count 1 --batteries 20 --unfolded --drone-battery 1
                                              jediná baterie, vybitá, v dronu (dron ji po přistání nabíjí ve slotu)
python tools/prepare_testsave.py --ibc 150    IBC s 150 l přípravku vlekem vedle vleku (přečerpání Alt+2)
python tools/prepare_testsave.py --drone L --battery-count 5
                                              velký dron s 5 bateriemi (konfigurace sprayDrone a sprayDroneBattery)
python tools/prepare_testsave.py --drone none vlek bez dronu (nabíjení baterií ve slotech a Alt+2 fungují)
python tools/prepare_testsave.py --battery-count 0
                                              dron bez baterií (nemůže vzlétnout)
python tools/prepare_testsave.py --water 800 --concentrate 40
                                              hlavní nádrž s 800 l vody a koncentrátová nádrž se 40 l koncentrátu tekutého hnojiva
                                              (mixér míchá přípravek při plnění dronu)
python tools/prepare_testsave.py --water 500 --concentrate 30 --concentrate-type herbicide
                                              totéž s koncentrátem herbicidu
python tools/prepare_testsave.py --water 500      voda bez koncentrátu (plánovač hlásí, že chybí koncentrát)
Elektrocentrála má ve výchozím stavu 20 l nafty. Ve výchozím stavu je dron M a 3 baterie (konfigurace v obchodě), plné, ve slotech.
"""

import argparse
import math
import os
import re
import uuid

SAVE = os.path.join(os.path.expanduser("~"), "Documents", "My Games", "FarmingSimulator2025", "savegame11")
MOD_NAME = "FS25_SprayDroneTrailer"
MOD_VERSION = "0.9.0.0"
TRAILER_XML = f"$moddir${MOD_NAME}/vehicles/sprayDroneTrailerMiddle/sprayDroneTrailerMiddle.xml"
MAX_TRAILER_XML = f"$moddir${MOD_NAME}/vehicles/sprayDroneTrailerMax/sprayDroneTrailerMax.xml"
MINI_TRAILER_XML = f"$moddir${MOD_NAME}/vehicles/sprayDroneTrailerMini/sprayDroneTrailerMini.xml"
MILL_XML = f"$moddir${MOD_NAME}/vehicles/sdtLimeMill/sdtLimeMill.xml"
MILL_REAR_Z = -9.17      # počátek vozíku za počátkem Maxu: koule věšáku i3d z -6,96, oj vozíku 2,21 m před počátkem
PICKUP_XML = "data/vehicles/lizard/pickup2017/pickup2017.xml"
# tahač: (xml, z oka v i3d tahače (dozadu je -z), index attacherJoint tahače, index inputAttacherJoint vleku podle --trailer)
# oka z i3d spočítal out/revize/T1/hitch_pos.py; vlek Middle má vstupy 1 trailerCar, 2 trailerLow, 3 trailer
TRACTORS = {
    "pickup": (PICKUP_XML, -2.758, 1, 1),
    "jd3650": ("data/vehicles/johnDeere/series3650/series3650.xml", -1.909, 3, 2),
    "jd3650high": ("data/vehicles/johnDeere/series3650/series3650.xml", -1.953, 2, 3),
    "mt655": ("data/vehicles/challenger/mt655/mt655.xml", -1.893, 3, 2),
    "mt655high": ("data/vehicles/challenger/mt655/mt655.xml", -1.936, 2, 3),
    "mf8570": ("data/vehicles/masseyFerguson/mf8570/mf8570.xml", -2.119, 2, 3),
    "rtv": ("data/vehicles/kubota/rtvx1140/rtvx1140.xml", -1.659, 1, 1),
}
IBC_XML = {"LIQUIDFERTILIZER": "data/objects/pallets/liquidTank/fertilizerTank.xml",
           "HERBICIDE": "data/objects/pallets/liquidTank/herbicideTank.xml"}
CONCENTRATE_TYPES = {"liquidfertilizer": "SDT_CONCENTRATE_FERTILIZER", "herbicide": "SDT_CONCENTRATE_HERBICIDE", "lime": "SDT_FINE_LIME"}
IBC_SIDE_OFFSET = 3.5             # IBC stojí vedle vleku (vpravo po směru jízdy), přečerpání dosáhne do 6 m
BATTERY_CONFIG = "sprayDroneBattery"   # saveId = počet baterií 0..5
DRONE_CONFIG = "sprayDrone"            # saveId NONE / S / M / L
DRONE_SAVE_IDS = {"none": "NONE", "S": "S", "M": "M", "L": "L"}
MAX_BATTERIES = 5
MARK = "sdt-test"
DIESEL_LITERS = 20.0
# cena vleku v obchodě (storeData) + dron + baterie po 1500 €, jen pro záznam v uložení
TRAILER_PRICE, DRONE_PRICES, BATTERY_PRICE = 6500, {"none": 0, "S": 7000, "M": 12000, "L": 22000}, 1500

# hráč se objevuje na (-783.8, 47.0, 132.7); souprava stojí u jižního okraje vlastního pole 4 (x -723..-671, z 176..293), čelem k +X
# (rotace v savegame je ve stupních, yaw 90 => dopředu = +X)
YAW_DEG = 90.0
PICKUP_POS = (-690.0, 47.5, 167.0)
# koule pickupu: i3d (0, 0.488, -2.758); spojka vleku: i3d (0, 0.50, 3.55) -> vlek o 6.308 m za pickupem
HITCH_OFFSET = 2.758 + 3.55
MINI_HITCH_OFFSET = 2.758 + 4.45  # oj Mini 1,85 m: i3d (0, 0.50, 4.45)
MAX_HITCH_OFFSET = 2.758 + 3.45  # tažné oko Maxu: i3d (0, 0.70, 3.45)
TRAILER_POS = (PICKUP_POS[0] - HITCH_OFFSET, PICKUP_POS[1], PICKUP_POS[2])
DEFAULT_TIME = "08:28"            # denní doba kopie slotu 5 (environment.xml dayTime v minutách)
PLAYER_SPAWN = ("-783.801025390625", "47.00000228881836", "132.73500061035156")
PLAYER_YAW = 128.380417


MISSION_MARK = "missionsdttest"
# pole 9: bavlna (růst 8), sprayLevel 0 -> cíl hnojení 1 (max sprayLevel mapy je 2), leží jen zčásti v dosahu;
# pole 8: kukuřice, plevel 3 -> herbicid 7 (data/maps/maps_weed.xml)
TEST_MISSIONS = [
    ("fertilizeMission", 9, 1, 'targetSprayLevel="1"'),
    ("herbicideMission", 8, 2, 'targetWeedState="7"'),
]


def mission_entry(kind, field_id, active_id, extra):
    return (f'    <{kind} uniqueId="{MISSION_MARK}{field_id}" status="RUNNING" finishState="NONE" farmId="1" '
            f'activeId="{active_id}" {extra}>\n'
            f'        <info reward="0" reimbursement="0.000000" completion="0.000000"/>\n'
            f'        <vehicles spawned="false" group="1"/>\n'
            f'        <endDate endDay="30" endDayTime="86399999"/>\n'
            f'        <field id="{field_id}"/>\n'
            f'    </{kind}>\n')


def uid():
    return "vehicle" + uuid.uuid4().hex


def vehicle_entry(filename, unique_id, pos, price, extra="", mod_name=None, yaw=YAW_DEG):
    mod_attr = f' modName="{mod_name}"' if mod_name else ""
    return (f'    <vehicle filename="{filename}"{mod_attr} uniqueId="{unique_id}" age="0.000000" price="{price:.6f}" '
            f'farmId="1" propertyState="OWNED" operatingTime="0.000000" tourId="{MARK}">\n'
            f'        <component index="1" position="{pos[0]:.3f} {pos[1]:.3f} {pos[2]:.3f}" rotation="0.00 {yaw:.2f} 0.00"/>\n'
            f'{extra}'
            f'    </vehicle>\n')


def dirt_entry(amount):
    """Špína (Washable, dirtNode) a opotřebení laku (Wearable, wearNode) vozidla v savegame."""
    return (f'        <washable>\n            <dirtNode amount="{amount:.6f}" wetness="0.000000"/>\n        </washable>\n'
            f'        <wearable damage="0.000000">\n            <wearNode amount="{amount:.6f}"/>\n        </wearable>\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trailer", choices=("middle", "max", "mini"), default="middle", help="middle = střední vlek za auto (výchozí), max = velký tandem se dvěma drony, mini = malý vlek s deskou")
    parser.add_argument("--tractor", choices=sorted(TRACTORS), default="pickup", help="tahač: pickup (výchozí), jd3650, mt655, mf8570, rtv (high = joint typu trailer místo trailerLow)")
    parser.add_argument("--slot", type=int, default=11, help="číslo slotu uložené hry (výchozí 11); slot se musí dřív zkopírovat ze slotu 5")
    parser.add_argument("--liters", type=float, default=300.0, help="litry v hlavní nádrži vleku (výchozí 300)")
    parser.add_argument("--tank", type=int, choices=(300, 800, 1000, 1500, 3000, 5000, 6000, 10000),
                        help="velikost hlavní nádrže vleku (konfigurace v obchodě; Max 6000 = 2 x 3000, 10000 = 2 x 5000; výchozí 1000 / 6000)")
    parser.add_argument("--wheels", help="saveId konfigurace kol, např. TRELLEBORG_T421_320_55R15 (Mini / Middle), CONTINENTAL_HYBRIDHD3_315_80R22_5 (Max) "
                        "nebo DEFAULT_TRELLEBORG_T421 (výchozí dynamická); bez údaje hra vybere výchozí")
    parser.add_argument("--mill", action="store_true", help="za Max zapřáhnout mlýnkový vozík na vápno (jen --trailer max)")
    parser.add_argument("--mill-lime", type=float, default=1500.0, help="hrubé vápno v nádobě vozíku (l)")
    parser.add_argument("--mill-diesel", type=float, default=30.0, help="nafta ve vozíku (l)")
    parser.add_argument("--player-at-mill", action="store_true", help="hráč pěšky 2,4 m vpravo od vozíku (s --mill)")
    parser.add_argument("--boxes-open", action="store_true", help="bedny / skříň na kanystry uložené otevřené (kontrola, že se samy nezavřou)")
    parser.add_argument("--rim-color", type=int, help="index (od 1) rimColorConfigurations: barva ráfků")
    parser.add_argument("--crate-color", type=int, help="index (od 1) baseColorConfigurations: barva bedny (Mini)")
    parser.add_argument("--stickers", help="saveId designConfigurations: FULL | LOGO | NONE (nálepky bedny, Mini)")
    parser.add_argument("--antenna", help="saveId sprayDroneAntennaConfigurations: NONE | BOOSTED | LARGE (Middle, Max)")
    parser.add_argument("--gps", help="saveId sprayDroneGpsConfigurations: STANDARD | RTK (Middle, Max)")
    parser.add_argument("--config", action="append", default=[], help="libovolná konfigurace vleku jako NAME=SAVEID, např. sprayDroneDeckEdge=WOOD (opakovatelné)")
    parser.add_argument("--generators", help="saveId sprayDroneGeneratorConfigurations: 1 | 2 (Max)")
    parser.add_argument("--herbicide", action="store_true", help="vlek naplnit herbicidem místo tekutého hnojiva")
    parser.add_argument("--water", type=float, help="hlavní nádrž vleku naplnit vodou (l) místo přípravku, pro míchání s koncentrátem")
    parser.add_argument("--concentrate", type=float, help="koncentrátová nádrž vleku (3. nádrž, kapacita 50 l): litry koncentrátu")
    parser.add_argument("--concentrate-type", choices=["liquidfertilizer", "herbicide", "lime"], default="liquidfertilizer",
                        help="koncentrát pro --concentrate: liquidfertilizer = SDT_CONCENTRATE_FERTILIZER, herbicide = SDT_CONCENTRATE_HERBICIDE, lime = SDT_FINE_LIME (Max i Middle; výchozí liquidfertilizer)")
    parser.add_argument("--diesel", type=float, default=DIESEL_LITERS, help="nafta v elektrocentrále (l)")
    parser.add_argument("--batteries", help="nabití baterií 1..N v %%, např. 35,40,30 (chybějící plné); všechny ve slotech vleku")
    parser.add_argument("--battery-count", type=int, help="počet baterií 0..5 (konfigurace v obchodě; výchozí počet hodnot "
                        "--batteries, jinak 3)")
    parser.add_argument("--drone", choices=sorted(DRONE_SAVE_IDS), default="M",
                        help="dron na vleku (konfigurace v obchodě): none = bez dronu, S / M / L; výchozí M")
    parser.add_argument("--drone-battery", type=int, help="baterie K (1..N) je v dronu, ne ve slotu (má smysl s --unfolded)")
    parser.add_argument("--ibc", type=float, nargs="?", const=200.0,
                        help="IBC s přípravkem jako ve vleku vedle vleku; hodnota = litry (výchozí 200, prázdnou hra smaže)")
    parser.add_argument("--ibc-behind", type=float, help="IBC (s --ibc) postavit tolik metrů přímo za vlek, např. 3.0 = do dráhy rozložené desky Mini")
    parser.add_argument("--time", default=DEFAULT_TIME, help="denní doba HH:MM (výchozí %s, noc např. 22:00)" % DEFAULT_TIME)
    parser.add_argument("--at", help="pickup jinam: x,y,z,yaw (vlek stojí za ním), např. u čerpací stanice")
    parser.add_argument("--unfolded", action="store_true", help="vlek rozložený (žebřík dole, dron rozložený)")
    parser.add_argument("--player-at-ladder", action="store_true", help="hráč pěšky 1,3 m vpravo od žebříku vleku (Middle, Max: pravý bok vzadu), čelem k němu")
    parser.add_argument("--player-at-tractor", action="store_true", help="hráč pěšky u levých dveří tahače, čelem k nim (E = nastoupit)")
    parser.add_argument("--player-at", help="hráč pěšky jinde: x,z,yaw (výška jako vlek), např. na poli u řádku")
    parser.add_argument("--canisters", type=int, help="počet naplněných kanystrů v hlavních slotech bedny (střídavě hnojivo / herbicid)")
    parser.add_argument("--canisters-same", action="store_true", help="všechny kanystry s hnojivem (test vyjmutí 16+ kusů)")
    parser.add_argument("--diesel-canisters", type=int, default=0, help="počet naplněných kanystrů nafty ve stojanu (s --canisters)")
    parser.add_argument("--dirt", type=float, help="špína a opotřebení zapřaženého vleku 0..1 (washable/wearable)")
    parser.add_argument("--showcase", action="store_true",
                        help="vedle soupravy dva odpojené rozložené vleky: S čistý (6 m vpravo) a L se špínou a "
                             "opotřebením 1,0 (12 m vpravo)")
    args = parser.parse_args()
    global SAVE, TRAILER_XML, HITCH_OFFSET, MAX_BATTERIES, TRAILER_POS
    SAVE = os.path.join(os.path.expanduser("~"), "Documents", "My Games", "FarmingSimulator2025", f"savegame{args.slot}")
    if args.tank is None:
        args.tank = {"max": 6000, "mini": 300}.get(args.trailer, 1000)
    if args.trailer == "mini":
        TRAILER_XML, HITCH_OFFSET = MINI_TRAILER_XML, MINI_HITCH_OFFSET
        TRAILER_POS = (PICKUP_POS[0] - HITCH_OFFSET, PICKUP_POS[1], PICKUP_POS[2])
    ladder_z = -3.0 if args.trailer == "mini" else -2.09
    if args.mill and args.trailer != "max":
        parser.error("--mill jen s --trailer max")
    if args.trailer == "max":
        TRAILER_XML, HITCH_OFFSET, MAX_BATTERIES, ladder_z = MAX_TRAILER_XML, MAX_HITCH_OFFSET, 8, -6.03
        TRAILER_POS = (PICKUP_POS[0] - HITCH_OFFSET, PICKUP_POS[1], PICKUP_POS[2])
    tractor_xml, tractor_hitch_z, tractor_joint, trailer_joint = TRACTORS[args.tractor]
    if args.trailer == "max":
        trailer_joint = {2: 2, 3: 1}.get(trailer_joint, 1)
    HITCH_OFFSET = HITCH_OFFSET - 2.758 - tractor_hitch_z
    TRAILER_POS = (PICKUP_POS[0] - HITCH_OFFSET, PICKUP_POS[1], PICKUP_POS[2])
    args.diesel = min(args.diesel, 30.0)
    fill_type = "HERBICIDE" if args.herbicide else "LIQUIDFERTILIZER"
    pickup_pos, trailer_pos, yaw = PICKUP_POS, TRAILER_POS, YAW_DEG
    if args.at:
        x, y, z, yaw = (float(c) for c in args.at.split(","))
        pickup_pos = (x, y, z)
        back = HITCH_OFFSET
        trailer_pos = (x - math.sin(math.radians(yaw)) * back, y, z - math.cos(math.radians(yaw)) * back)

    spawn, spawn_yaw = PLAYER_SPAWN, PLAYER_YAW
    if args.player_at_ladder:
        # Middle a Max: žebřík je vpravo vzadu v rovině boku (x -1,086, střed na z -2,09 / -6,03, dozadu je -z), hráč stojí 1,3 m vně
        # čelem k vozidlu (doleva); Mini žebřík nemá, hráč stojí 3 m za ním
        fx, fz = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
        lx, lz = (0.5, ladder_z) if args.trailer == "mini" else (-2.4, ladder_z)
        spawn = (trailer_pos[0] + lz * fx + lx * fz, trailer_pos[1] + 0.1, trailer_pos[2] + lz * fz - lx * fx)
        spawn_yaw = yaw if args.trailer == "mini" else yaw + 90.0
    elif args.player_at_mill:
        fx, fz = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
        lz = MILL_REAR_Z - 0.4
        spawn = (trailer_pos[0] + lz * fx - 2.4 * fz, trailer_pos[1] + 0.1, trailer_pos[2] + lz * fz + 2.4 * fx)
        spawn_yaw = yaw + 90.0
    elif args.player_at_tractor:
        fx, fz = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
        spawn = (pickup_pos[0] + 2.0 * fz + 0.3 * fx, pickup_pos[1] + 0.3, pickup_pos[2] - 2.0 * fx + 0.3 * fz)
        spawn_yaw = yaw - 90.0
    elif args.player_at:
        px, pz, spawn_yaw = (float(c) for c in args.player_at.split(","))
        spawn = (px, trailer_pos[1] + 0.3, pz)
    ppath = os.path.join(SAVE, "players.xml")
    pl = open(ppath, encoding="utf-8-sig").read()
    pl = re.sub(r'<spawn position="[^"]*" yaw="[^"]*"/>',
                f'<spawn position="{spawn[0]} {spawn[1]} {spawn[2]}" yaw="{spawn_yaw:.6f}"/>', pl, count=1)
    open(ppath, "w", encoding="utf-8-sig", newline="\n").write(pl)

    epath = os.path.join(SAVE, "environment.xml")
    e = open(epath, encoding="utf-8-sig").read()
    h, mnt = (int(c) for c in args.time.split(":"))
    e = re.sub(r"<dayTime>[^<]*</dayTime>", f"<dayTime>{h * 60 + mnt:.6f}</dayTime>", e, count=1)
    open(epath, "w", encoding="utf-8-sig", newline="\n").write(e)

    career = os.path.join(SAVE, "careerSavegame.xml")
    t = open(career, encoding="utf-8").read()
    t = re.sub(rf'\s*<mod modName="{MOD_NAME}"[^>]*/>', "", t)
    mod = f'<mod modName="{MOD_NAME}" title="Spray Drone Service Trailer" version="{MOD_VERSION}" required="true" fileHash=""/>'
    t = t.replace("</careerSavegame>", f"    {mod}\n</careerSavegame>")
    open(career, "w", encoding="utf-8", newline="\n").write(t)

    vpath = os.path.join(SAVE, "vehicles.xml")
    v = open(vpath, encoding="utf-8").read()
    v = re.sub(rf'    <vehicle [^>]*tourId="{MARK}".*?</vehicle>\n', "", v, flags=re.S)
    v = re.sub(rf'    <vehicle [^>]*modName="{MOD_NAME}"[^>]*>.*?</vehicle>\n', "", v, flags=re.S)
    trailer_id, pickup_id, mill_id = uid(), uid(), uid()
    hitch = (f'        <attacherJoints comboDirection="-1">\n'
             f'            <attachedImplement jointIndex="{tractor_joint}" moveDown="false" attachedVehicleUniqueId="{trailer_id}" inputJointIndex="{trailer_joint}"/>\n'
             f'        </attacherJoints>\n')
    main_type, main_level = ("WATER", args.water) if args.water is not None else (fill_type, args.liters)
    concentrate_unit = ""
    if args.concentrate is not None:
        concentrate_unit = (f'            <unit index="3" fillType="{CONCENTRATE_TYPES[args.concentrate_type]}" '
                            f'fillLevel="{args.concentrate:.6f}"/>\n')
    fill = ('        <fillUnit>\n'
            f'            <unit index="1" fillType="{main_type}" fillLevel="{main_level:.6f}"/>\n'
            f'            <unit index="2" fillType="DIESEL" fillLevel="{args.diesel:.6f}"/>\n'
            f'{concentrate_unit}'
            '        </fillUnit>\n')
    if args.unfolded:
        fill += '        <foldable foldAnimTime="0.000000" isAllowed="true"/>\n'
    percents = [float(c) for c in args.batteries.split(",")] if args.batteries else []
    count = args.battery_count if args.battery_count is not None else (len(percents) if percents else 3)
    if not 0 <= count <= MAX_BATTERIES:
        parser.error(f"--battery-count musí být 0..{MAX_BATTERIES}")
    if args.drone_battery is not None and not 1 <= args.drone_battery <= count:
        parser.error("--drone-battery musí být 1..počet baterií")
    if args.drone_battery is not None and args.drone == "none":
        parser.error("--drone-battery nejde s --drone none")
    percents = (percents + [100.0] * count)[:count]
    wheel_cfg = f'        <configuration name="wheel" id="{args.wheels}" isActive="true"/>\n' if args.wheels else ""
    for cfg_name, value in (("rimColor", args.rim_color), ("baseColor", args.crate_color), ("design", args.stickers),
                            ("sprayDroneAntenna", args.antenna), ("sprayDroneGps", args.gps),
                            ("sprayDroneGenerator", args.generators)):
        if value:
            wheel_cfg += f'        <configuration name="{cfg_name}" id="{value}" isActive="true"/>\n'
    for item in args.config:
        cfg_name, value = item.split("=", 1)
        wheel_cfg += f'        <configuration name="{cfg_name}" id="{value}" isActive="true"/>\n'
    fill = (wheel_cfg + f'        <configuration name="{DRONE_CONFIG}" id="{DRONE_SAVE_IDS[args.drone]}" isActive="true"/>\n'
            f'        <configuration name="{BATTERY_CONFIG}" id="{count}" isActive="true"/>\n'
            f'        <configuration name="fillUnit" id="TANK{args.tank}" isActive="true"/>\n' + fill)
    batteries, slot = "", 0
    for k, percent in enumerate(percents, start=1):
        if k == args.drone_battery:
            where = 0
        else:
            slot += 1
            where = slot
        batteries += f'            <battery level="{percent / 100:.4f}" slot="{where}"/>\n'
    canisters = ""
    if args.canisters or args.boxes_open:
        main_slots = {"max": 24, "mini": 4}.get(args.trailer, 12)
        total = {"max": 33, "mini": 4}.get(args.trailer, 15)
        for i in range(1, total + 1):
            if i <= main_slots:
                kind, liters = (CONCENTRATE_TYPES["herbicide"] if i % 2 == 0 and not args.canisters_same else CONCENTRATE_TYPES["liquidfertilizer"]), 20.0
                if i > (args.canisters or 0):
                    kind, liters = "UNKNOWN", 0.0
            else:
                kind, liters = ("DIESEL", 20.0) if i - main_slots <= args.diesel_canisters else ("UNKNOWN", 0.0)
            canisters += f'                <canister fillType="{kind}" liters="{liters:.1f}"/>\n'
        open_flag = "true" if args.boxes_open else "false"
        parts = "".join(f'                <part open="{open_flag}"/>\n' for _ in range(2 if args.trailer == "mini" else 1))
        canisters = '            <toolbox>\n' + canisters + parts + '            </toolbox>\n'
    fill += (f'        <{MOD_NAME}>\n'
             f'            <sprayDroneStation fieldId="0" missionActive="false" droneFillLevel="0" generatorEnabled="true">\n'
             f'{batteries}{canisters}'
             f'            </sprayDroneStation>\n'
             f'        </{MOD_NAME}>\n')
    if args.dirt is not None:
        fill += dirt_entry(args.dirt)
    if args.mill:
        fill += (f'        <attacherJoints>\n'
                 f'            <attachedImplement jointIndex="1" moveDown="false" attachedVehicleUniqueId="{mill_id}" inputJointIndex="3"/>\n'
                 f'        </attacherJoints>\n')
    entries = (vehicle_entry(tractor_xml, pickup_id, pickup_pos, 45000, hitch, yaw=yaw)
               + vehicle_entry(TRAILER_XML, trailer_id, trailer_pos, TRAILER_PRICE + DRONE_PRICES[args.drone] + BATTERY_PRICE * count, fill,
                               mod_name=MOD_NAME, yaw=yaw))
    if args.mill:
        fx, fz = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
        mill_pos = (trailer_pos[0] + MILL_REAR_Z * fx, trailer_pos[1], trailer_pos[2] + MILL_REAR_Z * fz)
        mill_fill = ('        <fillUnit>\n'
                     f'            <unit index="1" fillType="LIME" fillLevel="{args.mill_lime:.6f}"/>\n'
                     f'            <unit index="2" fillType="DIESEL" fillLevel="{args.mill_diesel:.6f}"/>\n'
                     '        </fillUnit>\n')
        entries += vehicle_entry(MILL_XML, mill_id, mill_pos, 16500, mill_fill, mod_name=MOD_NAME, yaw=yaw)
    if args.showcase:
        fx, fz = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
        for drone, side, dirt in (("S", 6.0, None), ("L", 12.0, 1.0)):
            pos = (trailer_pos[0] + fz * side, trailer_pos[1] + 0.4, trailer_pos[2] - fx * side)
            extra = (f'        <configuration name="{DRONE_CONFIG}" id="{drone}" isActive="true"/>\n'
                     f'        <configuration name="{BATTERY_CONFIG}" id="3" isActive="true"/>\n'
                     '        <fillUnit>\n'
                     f'            <unit index="1" fillType="{fill_type}" fillLevel="300.000000"/>\n'
                     f'            <unit index="2" fillType="DIESEL" fillLevel="{args.diesel:.6f}"/>\n'
                     '        </fillUnit>\n'
                     '        <foldable foldAnimTime="0.000000" isAllowed="true"/>\n'
                     + (dirt_entry(dirt) if dirt is not None else ""))
            entries += vehicle_entry(TRAILER_XML, uid(), pos, TRAILER_PRICE + DRONE_PRICES[drone] + BATTERY_PRICE * 3,
                                     extra, mod_name=MOD_NAME, yaw=yaw)
    ibc_pos = None
    if args.ibc is not None:
        # vpravo od vleku po směru jízdy (yaw 90 = +X, vpravo je -Z), kousek nad terénem, ať dopadne sama
        fx, fz = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
        ibc_pos = (trailer_pos[0] + fz * IBC_SIDE_OFFSET, trailer_pos[1] + 0.3, trailer_pos[2] - fx * IBC_SIDE_OFFSET)
        if args.ibc_behind:
            ibc_pos = (trailer_pos[0] - fx * args.ibc_behind, trailer_pos[1] + 0.3, trailer_pos[2] - fz * args.ibc_behind)
        ibc_fill = ('        <fillUnit>\n'
                    f'            <unit index="1" fillType="{fill_type}" fillLevel="{args.ibc:.6f}"/>\n'
                    '        </fillUnit>\n')
        entries += vehicle_entry(IBC_XML[fill_type], uid(), ibc_pos, 3200, ibc_fill, yaw=yaw)
    v = v.replace("</vehicles>", entries + "</vehicles>")
    open(vpath, "w", encoding="utf-8", newline="\n").write(v)

    mpath = os.path.join(SAVE, "missions.xml")
    m = open(mpath, encoding="utf-8").read()
    m = re.sub(rf'    <(\w+) uniqueId="{MISSION_MARK}\d+".*?</\1>\n', "", m, flags=re.S)
    m = m.replace("</missions>", "".join(mission_entry(*tm) for tm in TEST_MISSIONS) + "</missions>")
    open(mpath, "w", encoding="utf-8", newline="\n").write(m)
    print(f"mod v careerSavegame, pickup {pickup_id} @ {pickup_pos}, vlek {trailer_id} @ {trailer_pos} ({main_type} {main_level:.0f} l"
          + (f", koncentrát {args.concentrate_type} {args.concentrate:.0f} l" if args.concentrate is not None else "") + f", "
          f"nafta {args.diesel} l), zakázky na polích {[tm[1] for tm in TEST_MISSIONS]}, čas {args.time}")
    print(f"dron: {args.drone}; baterie: {count} ks, nabití {percents} %, v dronu {args.drone_battery or 'žádná'}"
          + (f"; IBC {args.ibc:.0f} l @ ({ibc_pos[0]:.1f}, {ibc_pos[1]:.1f}, {ibc_pos[2]:.1f})" if ibc_pos else ""))


if __name__ == "__main__":
    main()
