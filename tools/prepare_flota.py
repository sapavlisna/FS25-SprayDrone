"""Slot 11 načisto: smaže všechna vozidla farmy 1 a postaví tři vleky v nejvyšší výbavě, pumpu a mlýnek.

Mini: 300 l herbicidu, Middle: 5000 l tekutého hnojiva, Max (10000 l, prázdný) s připojeným mlýnkem (hrubé vápno plné) a vedle pumpa.
Voda všude prázdná, nafta všude plná, baterie plné ve slotech. Vozidla farmy 0 (vlaky, firemní vozidla mapy) zůstávají.
Záloha vehicles.xml a players.xml jde do out/save11_backup/.

python tools/prepare_flota.py
"""

import math
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
import prepare_testsave as pt

SAVE = os.path.join(os.path.expanduser("~"), "Documents", "My Games", "FarmingSimulator2025", "savegame11")
BACKUP = os.path.join(os.path.dirname(__file__), "..", "out", "save11_backup")
PUMP_XML = f"$moddir${pt.MOD_NAME}/objects/pump/waterPump.xml"
YAW = 90.0
X = -690.0
Y = 47.5
ROWS = {"mini": 150.0, "middle": 158.0, "max": 170.0, "pump": 180.0}


def configs(drone_batteries, extra):
    cfg = [("sprayDrone", "L"), ("sprayDroneBattery", str(drone_batteries))] + extra
    return "".join(f'        <configuration name="{n}" id="{i}" isActive="true"/>\n' for n, i in cfg)


def station(batteries):
    cells = "".join(f'            <battery level="1.0000" slot="{k}"/>\n' for k in range(1, batteries + 1))
    return (f'        <{pt.MOD_NAME}>\n'
            f'            <sprayDroneStation fieldId="0" missionActive="false" droneFillLevel="0" generatorEnabled="true">\n'
            f'{cells}'
            f'            </sprayDroneStation>\n'
            f'        </{pt.MOD_NAME}>\n')


def fill_units(*units):
    body = "".join(f'            <unit index="{i}" fillType="{t}" fillLevel="{l:.6f}"/>\n' for i, t, l in units)
    return f'        <fillUnit>\n{body}        </fillUnit>\n'


def vehicle(xml, pos, price, extra, mod=True):
    return pt.vehicle_entry(xml, pt.uid(), pos, price, extra, mod_name=pt.MOD_NAME if mod else None, yaw=YAW)


def main():
    os.makedirs(BACKUP, exist_ok=True)
    for name in ("vehicles.xml", "players.xml"):
        target = os.path.join(BACKUP, name)
        if not os.path.exists(target):
            shutil.copy(os.path.join(SAVE, name), target)

    vpath = os.path.join(SAVE, "vehicles.xml")
    v = open(vpath, encoding="utf-8").read()
    v, removed = re.subn(r'    <vehicle [^>]*farmId="1"[^>]*>.*?</vehicle>\n', "", v, flags=re.S)

    mini = vehicle(pt.MINI_TRAILER_XML, (X, Y + 0.4, ROWS["mini"]), 6500 + 7000 + 4 * 1500,
                   configs(4, [("fillUnit", "TANK300")])
                   + fill_units((1, "HERBICIDE", 300), (2, "DIESEL", 30)) + station(4))
    middle = vehicle(pt.TRAILER_XML, (X, Y + 0.4, ROWS["middle"]), 6500 + 22000 + 6 * 1500,
                     configs(6, [("fillUnit", "TANK5000"), ("sprayDroneAntenna", "LARGE"), ("sprayDroneGps", "RTK")])
                     + fill_units((1, "LIQUIDFERTILIZER", 5000), (2, "DIESEL", 30)) + station(6))
    mill_id = pt.uid()
    max_id = pt.uid()
    max_pos = (X, Y + 0.4, ROWS["max"])
    max_extra = (configs(10, [("fillUnit", "TANK10000"), ("sprayDroneGenerator", "2"),
                              ("sprayDroneAntenna", "LARGE"), ("sprayDroneGps", "RTK")])
                 + fill_units((1, "WATER", 0), (2, "DIESEL", 60)) + station(10)
                 + f'        <attacherJoints>\n'
                   f'            <attachedImplement jointIndex="1" moveDown="false" attachedVehicleUniqueId="{mill_id}" inputJointIndex="3"/>\n'
                   f'        </attacherJoints>\n')
    max_entry = pt.vehicle_entry(pt.MAX_TRAILER_XML, max_id, max_pos, 6500 + 22000 + 10 * 1500, max_extra, mod_name=pt.MOD_NAME, yaw=YAW)
    fx, fz = math.sin(math.radians(YAW)), math.cos(math.radians(YAW))
    mill_pos = (max_pos[0] + pt.MILL_REAR_Z * fx, max_pos[1], max_pos[2] + pt.MILL_REAR_Z * fz)
    mill = pt.vehicle_entry(pt.MILL_XML, mill_id, mill_pos, 16500,
                            fill_units((1, "LIME", 2400), (2, "DIESEL", 40)), mod_name=pt.MOD_NAME, yaw=YAW)
    pump = vehicle(PUMP_XML, (X, Y + 0.2, ROWS["pump"]), 1800, fill_units((1, "DIESEL", 15), (2, "WATER", 0)))

    v = v.replace("</vehicles>", mini + middle + max_entry + mill + pump + "</vehicles>")
    open(vpath, "w", encoding="utf-8", newline="\n").write(v)

    ppath = os.path.join(SAVE, "players.xml")
    pl = open(ppath, encoding="utf-8-sig").read()
    pl = re.sub(r'<spawn position="[^"]*" yaw="[^"]*"/>', f'<spawn position="{X + 12} {Y + 0.1} 165.0" yaw="270.000000"/>', pl, count=1)
    open(ppath, "w", encoding="utf-8-sig", newline="\n").write(pl)
    print(f"smazáno {removed} vozidel farmy 1; postaveno: Mini, Middle, Max + mlýnek, pumpa; hráč u nich")


if __name__ == "__main__":
    main()
