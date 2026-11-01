"""Servisní vlek pro jeden postřikový dron, menší verze za osobní auto (kulová spojka).

Stejné pojetí jako velká verze (build_trailer3.py): dole paluba s nádržemi a generátorem,
nahoře plošina pro dron. Podvozek porovnaný s vanilla FS25 Stema Trius (evropský valník za auto,
kolekce REF_StemaTrius): kola r 0,30, rozteč náprav 0,70, spojka 0,50-0,55 m nad zemí.

Hmotnost naplněného vleku ~1,3-1,5 t (nádrž 600 l), aby ho utáhlo běžné SUV.

Osa: spojka vpředu na -Y. Počátek = zem, střed šířky, střed paluby.
Staví se ve vlastním souboru spraydrone_trailer_middle.blend (jména objektů jsou v .blend globální
a shodují se s velkou verzí). Kolekci SprayDrone každé sestavení postaví znovu (build_drone.py, drony S, M = A, L)
a všechny tři posadí na střed heliportu.

Spuštění v Blenderu:
    p = r"...\\build_trailer_middle.py"; exec(open(p, encoding="utf-8").read(), {"__file__": p, "__name__": "__main__"})
Bez okna (přestavba + uložení + export): viz headless_middle.py.
"""

import importlib
import math
import os
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdt_parts as P  # noqa: E402
import sdt_tanks as T  # noqa: E402
import sdt_bigtank as BT  # noqa: E402
import sdt_labels as SL  # noqa: E402
import build_drone as D  # noqa: E402
import sdt_nozzle as N  # noqa: E402
import sdt_generator as G  # noqa: E402
import sdt_rims as RIMS  # noqa: E402

importlib.reload(P)
importlib.reload(T)
importlib.reload(BT)
importlib.reload(SL)
importlib.reload(D)
importlib.reload(N)
importlib.reload(G)
importlib.reload(RIMS)

COLLECTION_NAME = "SprayDroneTrailerMiddle"
PREVIEW_COLLECTION = "SprayDroneTrailerMiddle_Preview"   # jen do Blenderu, neexportuje se
COMPONENT_NAME = "sprayDroneTrailerMiddle_main_component1"
ROOT_NAME = "sprayDroneTrailerMiddle_vis"

# kolizní skupiny a masky převzaté z vanilla ABI Water Trailer 550
COL_VEHICLE = (0x10004, 0xfe3ffb83)
COL_TRIGGER = (0x20000000, 0x40000000)
COL_FILL_ROOT = (0x40000000, 0x20000000)

# --- paluba ---
BASE_LEN = 4.20
BASE_W = 2.10
BASE_Y0 = -BASE_LEN / 2
# vzadu je jen skříň na kanystry těsně za nádrží (Pavel 2026-10-11: zkrátit vůz); mezi zadní stěnou nádrže 5000 l (y 1,75) a
# skříní zůstává ~9 cm a nad skříní plošina s rezervou za složenými listy největšího dronu (y 1,88)
REAR_EXTRA = 0.16
BASE_Y1 = BASE_LEN / 2 + REAR_EXTRA
DECK_TOP = 0.72
DECK_PLATE = 0.035
RAIL_H = 0.18
RAIL_W = 0.06
IBEAM_X = 0.40
IBEAM_H = 0.14

# --- podvozek (vanilla pneu 320/60 R12, kategorie TRAILER; Pavel 2026-10-10: 500/45 R22,5 s rozteční 0,70 se navzájem
# prorůstala a procházela palubou - viz WHEEL_R). Pavel 2026-10-11: kola vně rámu (vedle vleku, ne pod ním) jako u Mini a Utili Trailer 2.
# Kola si hra generuje sama z rozměru pneumatiky; modelovaná kola jsou jen náhled.
TIRE_DIMENSIONS = "320_60R12"
WHEEL_R = 0.354                              # poloměr vanilla pneu 320/60 R12 (wheels.xml); 500/45 R22,5 (Ø 1,05) procházela palubou i sebou navzájem
WHEEL_W = 0.320
# jediná pneu bez výběru (Pavel 2026-10-13): silniční vlekové Lizard Destination Farm 280/70 R15 (r 0,385, TRAILER, tireType street)
# a vlastní disk sdtRim15; yOffset = rozdíl poloměru proti WHEEL_R, jako u dřívějších voleb. Model kola v Blenderu zůstává v poloměru
# WHEEL_R (poloha os a blatníků se nemění), hra pneu o 3 cm větší spustí dolů o yOffset.
TIRE_FILE = "$data/shared/wheels/tires/lizard/destinationFarm/280_70R15.xml"
TIRE_Y_OFFSET = 0.031
RIM_KIND, RIM_FILE, RIM_WIDTH_DIAM = "R15", "wheels/sdtRim15.i3d", "8 15.5"
LEGACY_WHEEL_IDS = ("DEFAULT_TRELLEBORG_T421", "TRELLEBORG_T421_320_55R15", "TRELLEBORG_T421_280_60R15_5",
                    "TRELLEBORG_AW305_10_80R12", "BKT_I1_11L_14", "BKT_PL801_250_70R15")
TIRE_REST_LOAD, TIRE_COMPRESSION, TIRE_SUSP_TRAVEL = 1.9, 12, 0.05
TIRE_SPRING, TIRE_DAMPER, TIRE_FRICTION = 200, 90, 1.9
TRACK_X = 1.23                               # osa kola; vnitřní líc pneu 1,07 těsně za stěnou krytu kola (1,055-1,063) u boční lišty (1,05)
AXLE_Y = [-0.05, 0.85]
# kryt kola vně rámu (vzhled podle Utili Trailer 2 a Mini): plechový oblouk od boční lišty přes kolo s přesahem, vnitřní stěna
# u lišty, vnější lem a zástěra za zadním kolem; stojí pevně na rámu, kolo se pod ním odpruží o TIRE_SUSP_TRAVEL
TIRE_R = 0.39                                # skutečný poloměr pneu Destination Farm 280/70 R15 ve hře (physics 0,385 + 0,005); střed kola je WHEEL_R + TIRE_Y_OFFSET
COVER_CLEAR = 0.04                           # vůle mezi pneu a plechem krytu (zdvih odpružení TIRE_SUSP_TRAVEL 0,05)
COVER_SHEET = 0.008
COVER_OVER = 0.02                            # kryt přesahuje pneu do stran
COVER_ARC = (-8.0, 188.0)                    # úhly (od +Y přes vrch) krytého oblouku
COVER_Z = WHEEL_R + TIRE_Y_OFFSET            # střed oblouku = osa kola ve hře
COVER_R_OUT = TIRE_R + COVER_CLEAR + COVER_SHEET
COVER_FLAP_W, COVER_FLAP_H = 0.30, 0.22
SUSP_LEAF_X = 0.70                           # listové pružiny pod deskou paluby mezi I-nosníkem a lištou
SUSP_LEAF_HALF = 0.34

# --- oj do A s kulovou spojkou ---
DRAWBAR_ROOT_X = 0.55
DRAWBAR_Z = 0.50
COUPLER_Y = -3.55
COUPLER_Z = 0.50

# --- horní plošina ---
TOP_SURF = 2.50
TOP_PLATE = 0.05
TOP_BEAM_H = 0.12
# přední hrana (Pavel 2026-10-15, plachta): přední sloupky, horní deska a prodloužená paluba nad ojí o 0,45 m před palubou;
# BASE_Y0 zůstává (oj, Mini a Max ji dědí), prodloužení staví build_front_extension
FRONT_Y = -2.55
TOP_Y0 = FRONT_Y
TOP_Y1 = BASE_Y1 + 0.20
TOP_W = BASE_W
POST = 0.08
POST_X = TOP_W / 2 - POST / 2
POST_Y = [FRONT_Y + 0.05, 0.0, BASE_Y1 - 0.07]
POST_TOP = TOP_SURF - TOP_PLATE - TOP_BEAM_H

# --- sklopný žebřík na pravém předním rohu (Pavel 2026-10-11, druhá verze) ---
# Složený žebřík je ZAVĚŠENÝ NAHOŘE Z BOKU: leží vodorovně podél pravého boku těsně pod horní deskou (kolejnice v rovině boku,
# délka po Y od čepu směrem LADDER_FOLD_DIR). Rozložený se jen SKLOPÍ DOLŮ o 90° kolem čepu na horním konci (osa X, kolmá na bok,
# kloub ladderHinge) a visí svisle dolů, dolní konec dosedne na zem; lezení z boku. Žádné vysouvání ani náklon.
# Madla (kloub ladderGrab, osa X v témže čepu) míří rozložená svisle nahoru nad desku a při skládání se sklopí opačným směrem
# vodorovně podél složeného žebříku (uvnitř jeho výšky), takže složený vlek nemá nic vyčnívajícího.
# Parametry pro velký vlek (Max): LADDER_HINGE_Y (poloha čepu po Y), LADDER_HINGE_Z (z LADDER_HINGE_DROP), LADDER_FOLD_DIR (+1 složený
# žebřík leží od čepu dozadu, -1 dopředu), LADDER_SIDE_X, LADDER_FOOT_Z, LADDER_W, LADDER_GRAB_UP.
LADDER_W = 0.38                  # rozteč kolejnic (po Y rozložený, výška složeného)
LADDER_RAIL_R = 0.022
LADDER_SIDE_X = -(TOP_W / 2 + 0.09)      # osa kolejnic: 9 cm vně rámu (vodítko hadice a hadice u předního rohu vyčnívají ~7 cm)
LADDER_HINGE_Y = BASE_Y0 + 0.40  # střed žebříku po Y: v předním rohu hned za pravou přední nohou (y -2,02), před vodítkem hadice (y -1,57)
LADDER_HINGE_DROP = 0.20         # čep tolik pod spodní hranou horních nosníků (složený žebřík pak končí těsně pod nápisem na boku)
LADDER_HINGE_Z = POST_TOP - LADDER_HINGE_DROP
LADDER_FOLD_DIR = 1.0            # složený žebřík leží od čepu směrem +Y (dozadu) / -Y (dopředu)
LADDER_FOOT_Z = 0.25             # spodek kolejnic rozloženého žebříku nad zemí (jako zasunutá noha; delší žebřík by se při sklápění
                                 # otáčel do předního krytu kola, spouštěč lezení sahá až k zemi)
LADDER_COL_MIN_Z = 0.25          # spodek kolize žebříku nad zemí
LADDER_COL_THICKNESS = 0.10
LADDER_GRAB_UP = 0.75            # madla (rozložená) nad horní deskou
LADDER_GRAB_W = 0.26             # rozteč madel (užší než kolejnice, ať se složená vejdou do výšky žebříku)
LADDER_GRAB_GAP = 0.03           # mezera mezi čepem a madlem
LADDER_GRAB_R = 0.020
LADDER_GRAB_TIME = (2.0, 2.6)    # s ve foldLadder: stejně jako sklápění žebříku

# skříň na kanystry (Pavel 2026-10-07/09): nahrazuje bývalou bednu s víkem + samostatný stojan na naftu (bez
# rozlišení obsahu, žádný slot není vyhrazený). Zadní stěna u y0 (směrem k nádrži), rolovací vrata u y1 (směrem ven
# z vleku) - viz build_cabinet_door. CABINET_LEVELS pater nad sebou, v každém patře CABINET_ROWS řad po CABINET_COLS
# kanystrech stojících na výšku. Hloubka (y0 -> y1) jde jen těsně za poslední řadu (cabinet_depth) - Pavel 2026-10-09:
# až k zadní hraně vleku to zbytečně prohlubovalo prázdnou předsíňku před vraty.
CABINET_WALL = 0.012
CABINET_DIV = 0.010
CABINET_LEVEL_CLEARANCE = 0.03              # nad kanystrem do police dalšího patra
CABINET_ROWS = 2                            # Pavel 2026-10-09: 4 řady za sebou byly zbytečně hluboké, stačí 2
CABINET_COLS = 6
CABINET_LEVELS = 4
CABINET_DOOR_GAP = 0.03                     # mezera mezi poslední řadou kanystrů a vraty (vodítko vrat)


REAR_CROSS_OFFSET = 0.14                         # zadní příčník kousek před zadní hranou desky (Max má vlastní)


def cabinet_ceiling():
    """Do jaké výšky jde skříň: až pod horní plošinu (nad posledním patrem plný strop bez polic)."""
    return TOP_SURF - TOP_PLATE


def cabinet_depth(rows=CABINET_ROWS):
    _, D, _ = T.CANISTER
    sd = D + 0.020
    return CABINET_WALL + rows * sd + CABINET_DOOR_GAP


def cabinet_y_range(rows=CABINET_ROWS):
    """Skříň na samém konci vleku: vrata v rovině se zadní hranou rámu (BASE_Y1), zadní stěna směrem k nádrži
    (Pavel 2026-10-09). Uvolněné místo před skříní zůstává nádrži."""
    return BASE_Y1 - cabinet_depth(rows), BASE_Y1

# lezení po žebříku (vanilla LadderTrigger): spouštěč ladderTrigger kolem žebříku, vně od něj LADDER_TRIGGER_OUT, nahoře o
# LADDER_TRIGGER_UP nad závěsem; hráč v něm leze normálním pohybem
LADDER_TRIGGER_OUT = 0.75
LADDER_TRIGGER_IN = 0.20           # za osu žebříku k vleku (hráč na horním konci přestoupí na desku, sahá k x -0,94 jako dřív)
LADDER_TRIGGER_UP = 0.70

DRONE_Y = 0.0
# tři velikosti dronu (build_drone.SPECS), všechny v i3d na středu heliportu, viditelnost řídí konfigurace
DRONE_VARIANTS = {"S": "Drone_S_", "M": "Drone_A_", "L": "Drone_L_"}
DRONE_PREFIX = DRONE_VARIANTS["M"]
DRONE_HIDDEN = ("S", "L")         # v i3d skryté (visibility false), výchozí je M
DRONE_COLLECTION = "SprayDrone"
DRONE_TILT_Z = {"S": 0.53, "M": 0.55, "L": 0.65}   # kloub náklonu za letu, nad lyžinami
# LED pod motory: přední ramena (1, 2) červená, zadní (3, 4) zelená jako u DJI Agras; barva jde do barvy vrcholů,
# svit řídí skript parametrem lightIds0 (vehicleShader staticLight_vertex)
LED_COLORS = {1: (1.0, 0.03, 0.02), 2: (1.0, 0.03, 0.02), 3: (0.03, 1.0, 0.08), 4: (0.03, 1.0, 0.08)}
LED_SIZE = (0.07, 0.07, 0.025)
LED_LIGHT_RANGE = 3.0
# úchyty lyžin dronu: dva na každé lyžině mezi příčkou a nohami, čelist se při skládání vleku překlopí přes trubku
CLAMP_Y = (-0.075, 0.075)
CLAMP_W = 0.07
CLAMP_POST = 0.04
CLAMP_GAP = 0.01
CLAMP_JAW_T = 0.02
CLAMP_OPEN_DEG = 100
CLAMP_TIME = (2.0, 2.4)            # s ve foldLadder: po složení dronu (0–2 s), souběžně s vyklopením žebříku
GEN_POS = (0.55, -1.35)
# Middle (2026-10-15): centrála o 0,45 m dopředu na prodlouženou palubu. GEN_POS zůstává, Max z ní počítá těžiště
# (export_max_mod.center_of_mass)
GEN_SHIFT_Y = -0.45
GEN_POS_MIDDLE = (GEN_POS[0], GEN_POS[1] + GEN_SHIFT_Y)

JOCKEY_X, JOCKEY_Y = 0.30, COUPLER_Y + 0.75
JOCKEY_LIFT = 0.35                # o kolik se kolečko při zapřažení zvedne
# kolize kolečka (vzor supportCol ABI Water Trailer 550): odpojený vlek na ní stojí, animace moveSupport ji zvedá
JOCKEY_COL = (0.06, 0.10, 0.22)   # půl šířky, půl délky, výška nad zemí

# heliport pod dronem: tmavý kruh, bílé mezikruží a "H" (vrstvy nad palubou kvůli z-fightingu)
# (lyžiny S x ±0,34, M ±0,42, L ±0,56 leží vně H; rohy lyžin L uvnitř mezikruží)
HELI_R = 0.98
HELI_RING = (0.83, 0.93)
HELI_H = (0.56, 0.90, 0.12)       # šířka, výška (po Y), tloušťka čar
HELI_LAYER = 0.003

# baterie: držák u centrály (stojí konektorem dolů, po Y za sebou) a nabíječka v levém předním rohu horní paluby
BATTERY_COUNT = 6
BATTERY_MAX = P.BATTERY_SIZES["L"]  # držák i šachty nabíječky musí pojmout největší (DB2160)
DRONE_BATTERY = {"S": (0.0, 0.18), "M": (0.0, 0.215), "L": (0.0, 0.24)}      # xy baterie na hřbetu trupu (vzadu, napříč)
DRONE_FILL_PORT = {"S": (-0.145, -0.04), "M": (-0.17, -0.10), "L": (-0.20, -0.12)}  # plnicí hrdlo na straně hadice (vpravo, -X), vedle radaru

# nabíječka: šachty 2 × 3 (baterie stojí konektorem dolů, rukojetí nahoru); šikmý ovládací panel v šesté buňce zrušen
# (Pavel 2026-10-15), je tam šestá šachta. U každé šachty 5 diod Charger_Led_<šachta>_<n> (n 0 červená, 1-2 oranžová, 3-4 zelená),
# skript jich rozsvítí ceil(nabití * 5)
CHARGER_CELL_X = (0.35, 0.655)
CHARGER_CELL_Y = (-2.05, -1.86, -1.67)
CHARGER_SHAFT = (BATTERY_MAX[1] + 0.02, BATTERY_MAX[2] + 0.02)
CHARGER_WALL = 0.035
CHARGER_FEET = 0.015
CHARGER_DOCK = 0.035              # výška dna šachet nad spodkem těla
CHARGER_SLOTS = [(0, 0), (1, 0), (0, 1), (1, 1), (1, 2), (0, 2)]
CHARGER_EXPOSED = 0.025           # o kolik tělo baterie vyčnívá nad nabíječku (plus rukojeť)
CHARGER_LED_MATS = ("SDT_LampRed", "SDT_LampAmber", "SDT_LampAmber", "SDT_LedGreen", "SDT_LedGreen")
CHARGER_LED_PITCH = 0.03
CHARGER_LED_LEN = 0.02
CABLE_R = 0.01
CHARGER_SOCKET_Y, CHARGER_SOCKET_Z = -1.67, 0.18    # zásuvka na levé vnější stěně truhly (výška nad podlahou truhly)
# truhla nabíječky na horní palubě: stěny kolem nabíječky, víko na předním závěsu (chargerLid), otevřené = rozložený vlek
CHEST_WALL = 0.03
CHEST_GAP_X, CHEST_GAP_Y = 0.06, 0.05
CHEST_LID_CLEAR = 0.13            # světlá výška nad okrajem nabíječky (rukojeti největších baterií)
CHEST_LID_T = 0.03
CHEST_RIM = 0.015                 # o kolik okraj stěn truhly přesahuje horní desku (víko na něm leží, truhla je zapuštěná)
CHEST_OPEN_DEG = 92
CHEST_LID_TIME = (1.8, 3.0)       # s ve foldLadder: víko se zavírá při skládání dronu, kabel se odpojí hned na začátku
CHEST_CABLE_TIME = (0.0, 0.05)
GEN_SOCKET = (0.88, -1.45 + GEN_SHIFT_Y, 1.15)       # zásuvka na levém boku elektrocentrály

# modrý navíječ pod plošinou vpředu vpravo, hadice z něj svisle nahoru vnitřkem (za zadní stranou bubnu) a průchodkou v horní
# desce (Pavel 2026-10-15: přes bok a lem by kolidovala s rolí plachty), pak volně po přední části desky (před heliportem,
# vedle nabíječky); k dronu jde zepředu mezi předními rameny
REEL = (-POST_X + 0.18, -1.78, POST_TOP - 0.30)
REEL_R = 0.18
HOSE_R = 0.02
HOSE_SEGMENTS = 96
HOSE_LEAD = 0.16                  # posledních 0,16 m hadice je rovně v ose koncovky (= Lua HOSE_NOZZLE_LEAD)
HOSE_COIL_R = REEL_R + HOSE_R
HOSE_Z = TOP_SURF + HOSE_R + 0.006
HOSE_HOLE = (-0.90, -1.49)        # průchodka v horní desce (uvnitř TopBeam, nad zadní hranou bubnu)
HOSE_FEED = [(REEL[0] - 0.08, REEL[1] + HOSE_COIL_R, REEL[2]), (-0.905, -1.545, 2.20), (-0.90, -1.50, 2.36)]
HOSE_START = (HOSE_HOLE[0], HOSE_HOLE[1], TOP_SURF - 0.03)       # v průchodce, hadice z ní vychází na desku
# tvar volně položené hadice; Lay1-2 hned za průchodkou, Lay3 = konec pevného úseku (Lua HOSE_FIXED_LAY), Lay6-8 doplní
# hose_lay_points (nájezd, konec, špička)
HOSE_LAY = [(-0.897, -1.43, HOSE_Z), (-0.88, -1.31, HOSE_Z), (-0.86, -1.20, HOSE_Z), (-0.30, -1.08, HOSE_Z),
            (-0.12, -1.42, HOSE_Z)]
HOSE_PARK_TIP = (-0.70, -2.02, HOSE_Z + 0.006)
HOSE_PARK_DIR = (-0.97, -0.25, 0.0)       # špička koncovky míří doleva, přívod hadice šikmo do paluby (spoušť k hraně)
NOZZLE_LIFT = 0.004               # koncovka leží na boku (spoušť do strany), tělo je širší než hadice

SIDE_MARKER_R_Y = BASE_Y1 - 0.12
# Middle: poziční světla na konzolách za koncem boční plachty na zadním rohu (na podélníku by je plachta zakryla), svítí do boku
SIDE_MARKER_POS = (1.17, BASE_Y1 + 0.03, 0.63)

# uzly pro sdílená světla hry: (jméno, poloha v Blenderu, natočení v i3d ve stupních) podle Stema Trius
LIGHT_NODES = [
    ("rearLight52_left", (0.86, BASE_Y1 + 0.005, DECK_TOP - RAIL_H + 0.08), (-90, 0, 180)),
    ("rearLight52_right", (-0.86, BASE_Y1 + 0.005, DECK_TOP - RAIL_H + 0.08), (-90, 0, 180)),
    ("plateNumberLight03", (0.0, BASE_Y1 + 0.005, DECK_TOP - RAIL_H - 0.005), (-90, 0, -90)),
    ("sideMarker05_left", SIDE_MARKER_POS, (0, 0, -90)),
    ("sideMarker05_right", (-SIDE_MARKER_POS[0],) + SIDE_MARKER_POS[1:], (0, 0, 90)),
]
EXIT_POINT = (BASE_W / 2 + 1.0, TOP_Y1 - 0.6, 0.0)
CAMERA_TARGET = (0.0, DRONE_Y, TOP_SURF + 1.0)

# plnicí uzel kryje největší hlavní nádrž (5000 l, hranatá); menší velikosti (sdt_bigtank) se do ní vejdou
# skříň je na samém konci vleku, takže se nádrž 5000 l prodlouží až skoro k její zadní stěně (poctivých 5000 l místo
# ~4000 l; 1,84 x 1,34 x 2,04 m) - Pavel 2026-10-09. Max (dvě nádrže za sebou) si délku nechává, jeho zdroj vlajku vypne.
CAR_LONG_TANK = True
if CAR_LONG_TANK:
    BT.L.BOX_GEOM[5000] = (BT.L.BOX_GEOM[5000][0], BT.L.BOX_GEOM[5000][1], 2.04)
TANK_R, TANK_LEN, TANK_TOP = BT.tank_envelope(max(BT.TANK_SIZES))
TANK_Y = BT.MAIN_TANK_Y_FRONT + TANK_LEN / 2

box, tube, plate_yz, cylinder_x, cylinder_z, capsule, empty = (
    P.box, P.tube, P.plate_yz, P.cylinder_x, P.cylinder_z, P.capsule, P.empty)


def build_chassis():
    rail_z0 = DECK_TOP - RAIL_H
    for side, sx in (("L", 1), ("R", -1)):
        x_out = sx * BASE_W / 2
        box(f"Rail_{side}", x_out, x_out - sx * RAIL_W, BASE_Y0, BASE_Y1, rail_z0, DECK_TOP, "SDT_Frame")
        box(f"IBeam_{side}", sx * IBEAM_X - 0.04, sx * IBEAM_X + 0.04, BASE_Y0, BASE_Y1,
            DECK_TOP - DECK_PLATE - IBEAM_H, DECK_TOP - DECK_PLATE, "SDT_Frame")
        P.reflective_tape(f"Tape_{side}", x_out, sx, BASE_Y0 + 0.05, BASE_Y1 - 0.05, rail_z0 + 0.05, rail_z0 + 0.12,
                          seg=0.25)
    box("Deck", -BASE_W / 2 + RAIL_W, BASE_W / 2 - RAIL_W, BASE_Y0, BASE_Y1,
        DECK_TOP - DECK_PLATE, DECK_TOP - 0.005, "SDT_DeckWood")
    box("FrontBeam", -BASE_W / 2, BASE_W / 2, BASE_Y0, BASE_Y0 + 0.08, rail_z0, DECK_TOP, "SDT_Frame")
    box("RearBeam", -BASE_W / 2, BASE_W / 2, BASE_Y1 - 0.08, BASE_Y1, rail_z0, DECK_TOP, "SDT_Frame")
    box("LicensePlateMount", -0.28, 0.28, BASE_Y1 - 0.06, BASE_Y1, rail_z0 - 0.14, rail_z0, "SDT_Frame")

    for i, ay in enumerate(AXLE_Y, 1):
        for side, sx in (("L", 1), ("R", -1)):
            c = Vector((sx * TRACK_X, ay, WHEEL_R))
            RIMS.build_tire(f"Wheel_{i}{side}", sx, WHEEL_R, WHEEL_W, RIMS.RIMS[RIM_KIND]["bead"]).matrix_world = Matrix.Translation(c)
            RIMS.build_rim(RIM_KIND, f"Rim_{i}{side}", sx).matrix_world = Matrix.Translation(c)


def _cover_prism(name, y_c, z_c, r0, r1, a0, a1, x0, x1, mat, steps=32):
    """Výseč mezikruží r0..r1 v rovině YZ (úhel od osy +Y přes +Z), vytažená po X od x0 do x1: plech krytu kola."""
    bm = bmesh.new()
    ring = []
    for k in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * k / steps)
        c, s_ = math.cos(a), math.sin(a)
        ring.append([bm.verts.new((x, y_c + r * c, z_c + r * s_)) for x in (x0, x1) for r in (r0, r1)])
    for k in range(steps):
        a_, b_ = ring[k], ring[k + 1]
        for i, j in ((0, 1), (1, 3), (3, 2), (2, 0)):
            bm.faces.new((a_[i], a_[j], b_[j], b_[i]))
    for end in (ring[0], ring[-1]):
        bm.faces.new((end[0], end[1], end[3], end[2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return P._finish(name, bm, Matrix.Identity(4), mat, smooth_quads=True)


def build_middle_suspension():
    """Odpružení tandemu pod deskou, kola jsou venku: hranatá náprava pod deskou, na každé straně mezi I-nosníkem a lištou svazek
    pěti listů (nejdelší nahoře, oka a třmeny na koncích, úchyty k desce), třmenové šrouby s přítlačnou deskou, brzdový buben a náboj
    těsně za pneu (BrakeDrum_ / Hub_ jedou v i3d s kolem). Vzor: Mini (stejné listové pružení)."""
    frame, steel = "SDT_Frame", "SDT_Steel"
    axle_top = WHEEL_R + 0.035
    stub = TRACK_X - WHEEL_W / 2 - 0.07                 # konec nápravy těsně u náboje, který stojí hned za pneu
    leaf_t, leaf_gap = 0.010, 0.012
    z_main = axle_top + 4 * leaf_gap + leaf_t
    z_below = DECK_TOP - DECK_PLATE
    rise = 0.095
    for n, ay in enumerate(AXLE_Y, 1):
        box(f"Axle_{n}", -stub, stub, ay - 0.035, ay + 0.035, WHEEL_R - 0.035, axle_top, frame)
        for side, sx in (("L", 1), ("R", -1)):
            tag = f"{n}{side}"
            xs = sx * SUSP_LEAF_X
            for k, half in enumerate((SUSP_LEAF_HALF, 0.28, 0.22, 0.16, 0.10)):
                stations = []
                for i in range(9):
                    u = -1 + i / 4
                    y = ay + half * u
                    yy = (y - ay) / SUSP_LEAF_HALF
                    top = z_main + rise * yy * yy - k * leaf_gap
                    stations.append((y, 0.030, top - leaf_t, top, 8))
                P.loft_y(f"Leaf_{tag}{k}", stations, steel, x=xs, segments=12)
            box(f"LeafSeat_{tag}", xs - 0.045, xs + 0.045, ay - 0.075, ay + 0.075, z_main, z_main + 0.014, frame)
            box(f"LeafClamp_{tag}", xs - 0.05, xs + 0.05, ay - 0.07, ay + 0.07, WHEEL_R - 0.035 - 0.014, WHEEL_R - 0.035, frame)
            for dy in (-0.045, 0.045):
                for dx in (-0.034, 0.034):
                    tube(f"UBolt_{tag}{dx:+.2f}{dy:+.2f}", (xs + dx, ay + dy, WHEEL_R - 0.055), (xs + dx, ay + dy, z_main + 0.034),
                         0.007, steel, segments=8)
            for e in (-1, 1):
                yc = ay + e * SUSP_LEAF_HALF
                eye_z = z_main + rise
                tube(f"LeafEye_{tag}{e:+d}", (xs - 0.034, yc, eye_z - leaf_t / 2), (xs + 0.034, yc, eye_z - leaf_t / 2), 0.016,
                     steel, segments=12)
                for dx in (-0.044, 0.044):
                    box(f"LeafHanger_{tag}{e:+d}{dx:+.2f}", xs + dx - 0.004, xs + dx + 0.004, yc - 0.025, yc + 0.025,
                        eye_z - 0.02, z_below, frame)
            side_rear = ay + SUSP_LEAF_HALF
            box(f"LeafShackleBar_{tag}", xs - 0.044, xs + 0.044, side_rear + 0.02, side_rear + 0.026, z_main + rise - 0.02,
                z_main + rise + 0.03, steel)
            cylinder_x(f"BrakeDrum_{tag}", (sx * (TRACK_X - WHEEL_W / 2 - 0.03), ay, WHEEL_R), 0.11, 0.05, "SDT_CastIron",
                       segments=24)
            cylinder_x(f"Hub_{tag}", (sx * (TRACK_X - WHEEL_W / 2 - 0.045), ay, WHEEL_R), 0.05, 0.05, steel, segments=16)


def build_wheel_arches():
    """Podvozek tandemu s koly vně rámu: odpružení pod deskou (build_middle_suspension) a kryty kol: plechový oblouk od boční
    lišty přes pneu s přesahem, vnitřní stěna u lišty (s otvorem pro nápravu), vnější lem, držáky k liště a gumová zástěra za
    zadním kolem. Jen vizuál, jen Middle (Mini a Max mají vlastní podvozek a blatníky)."""
    build_middle_suspension()
    r_out = COVER_R_OUT
    r_in = r_out - COVER_SHEET
    rail_x = BASE_W / 2
    a0, a1 = COVER_ARC
    for side, sx in (("L", 1), ("R", -1)):
        x_edge = sx * (TRACK_X + WHEEL_W / 2 + COVER_OVER)
        x_rail = sx * (rail_x + 0.005)
        # plech končí o 4 mm uvnitř stěny a lemu, ať se jejich plochy nekryjí (z-fighting); stěna a lem jsou o 2 mm pod vnějším povrchem
        xa, xb = sorted((x_rail + sx * 0.004, x_edge - sx * 0.004))
        wall = sorted((x_rail, x_rail + sx * COVER_SHEET))
        lip = sorted((x_edge, x_edge - sx * COVER_SHEET))
        for n, ay in enumerate(AXLE_Y, 1):
            tag = f"{side}{n}"
            _cover_prism(f"WheelArch_{tag}", ay, COVER_Z, r_in, r_out, a0, a1, xa, xb, "SDT_PaintDark")
            _cover_prism(f"WheelArchInner_{tag}", ay, COVER_Z, 0.22, r_out - 0.002, a0 + 0.5, a1 - 0.5, *wall, "SDT_PaintDark")
            _cover_prism(f"WheelArchLip_{tag}", ay, COVER_Z, r_out - 0.05, r_out - 0.002, a0 + 0.5, a1 - 0.5, *lip, "SDT_PaintDark")
            for e, ang in (("F", 165.0), ("R", 15.0)):
                a = math.radians(ang)
                yb, zb = ay + (r_out - 0.02) * math.cos(a), COVER_Z + (r_out - 0.02) * math.sin(a)
                box(f"WheelArchBracket_{tag}{e}", min(sx * rail_x, sx * (rail_x + 0.01)), max(sx * rail_x, sx * (rail_x + 0.01)),
                    yb - 0.03, yb + 0.03, zb - 0.05, zb + 0.01, "SDT_Frame")
        xw = sx * TRACK_X
        yf = AXLE_Y[-1] + WHEEL_R + 0.045
        zf = WHEEL_R * 0.55 + COVER_FLAP_H
        box(f"MudflapBar_{side}", xw - COVER_FLAP_W / 2 - 0.01, xw + COVER_FLAP_W / 2 + 0.01, yf - 0.012, yf + 0.012, zf - 0.015,
            zf + 0.012, "SDT_Frame")
        box(f"Mudflap_{side}", xw - COVER_FLAP_W / 2, xw + COVER_FLAP_W / 2, yf - 0.006, yf + 0.006, zf - 0.015 - COVER_FLAP_H,
            zf - 0.015, "SDT_Rubber")
        box(f"MudflapWeight_{side}", xw - COVER_FLAP_W / 2, xw + COVER_FLAP_W / 2, yf - 0.011, yf + 0.011,
            zf - 0.015 - COVER_FLAP_H, zf - 0.015 - COVER_FLAP_H + 0.03, "SDT_Rubber")


def build_drawbar():
    tip = Vector((0, COUPLER_Y + 0.25, DRAWBAR_Z))
    for side, sx in (("L", 1), ("R", -1)):
        root = Vector((sx * DRAWBAR_ROOT_X, BASE_Y0 + 0.40, DRAWBAR_Z))
        tube(f"Drawbar_{side}", root, tip, 0.045, "SDT_Frame", segments=8)
        box(f"DrawbarMount_{side}", root.x - 0.06, root.x + 0.06, BASE_Y0, BASE_Y0 + 0.45,
            DRAWBAR_Z - 0.05, DECK_TOP - DECK_PLATE, "SDT_Frame")
    build_coupler(tip)
    # opěrné kolečko: pevná objímka + pohyblivá skupina jockeyWheel (animace moveSupport ji zvedá)
    jx, jy = JOCKEY_X, JOCKEY_Y
    box("Jockey_Clamp", jx - 0.14, jx + 0.04, jy - 0.05, jy + 0.05, DRAWBAR_Z - 0.04, DRAWBAR_Z + 0.06, "SDT_Frame")
    moving = [
        tube("Jockey_Tube", (jx, jy, 0.20), (jx, jy, DRAWBAR_Z + 0.30), 0.03, "SDT_Steel", segments=12),
        tube("Jockey_Crank", (jx, jy, DRAWBAR_Z + 0.30), (jx, jy, DRAWBAR_Z + 0.36), 0.012, "SDT_Frame", segments=8),
        box("Jockey_Fork", jx - 0.05, jx + 0.05, jy - 0.03, jy + 0.03, 0.08, 0.21, "SDT_Steel"),
        cylinder_x("Jockey_Wheel", (jx, jy, 0.10), 0.10, 0.07, "SDT_Rubber", segments=20),
    ]
    pivot = empty("jockeyWheel", (jx, jy, DRAWBAR_Z))
    for o in moving:
        w = o.matrix_world.copy()
        o.parent = pivot
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_world = w
    cx, cy, cz = JOCKEY_COL
    _shape_box("colJockeyWheel", pivot, jx - cx, jx + cx, jy - cy, jy + cy, 0.0, cz, COL_VEHICLE,
               compoundChild=True, density=0.001)
    # vanilla přívěsy mají attacherJoint v i3d natočený "0 90 0" (osa Y i3d = osa Z Blenderu)
    aj = empty("attacherJoint", (0, COUPLER_Y, COUPLER_Z))
    aj.rotation_euler = (0, 0, math.radians(90))


def build_coupler(tip):
    """Nájezdová brzda s kulovou hlavou (styl přívěsů za auto): střed koule tažného zařízení = attacherJoint
    (0, COUPLER_Y, COUPLER_Z). Hlava s rukojetí a ukazatelem opotřebení, táhlo v gumovém měchu, skříň nájezdu na
    vrcholu oje, ruční brzda s pákou a plynovou vzpěrou, táhlo brzdy, pojistné lanko s karabinou a kabel 13pin
    se zástrčkou. Jen vizuál: kolize colDrawbar a geometrie tažení se nemění."""
    by, bz = COUPLER_Y, COUPLER_Z
    az = bz + 0.027                                   # osa táhla a skříně
    P.loft_y("Coupler_Head", [
        (by - 0.062, 0.020, bz + 0.015, bz + 0.050, 2.5), (by - 0.050, 0.036, bz, bz + 0.066, 3.0),
        (by - 0.020, 0.046, bz - 0.008, bz + 0.074, 3.5), (by + 0.030, 0.046, bz - 0.008, bz + 0.076, 3.5),
        (by + 0.060, 0.040, bz, bz + 0.066, 3.0), (by + 0.080, 0.030, bz + 0.005, bz + 0.050, 2.5)],
        "SDT_CastIron")
    tube("Coupler_Handle", (0, by - 0.045, bz + 0.072), (0, by + 0.12, bz + 0.107), 0.011, "SDT_CastIron", segments=10)
    tube("Coupler_HandleGrip", (0, by + 0.10, bz + 0.103), (0, by + 0.165, bz + 0.116), 0.016, "SDT_PaintRed",
         segments=12)
    cylinder_x("Coupler_WearRing", (0.047, by + 0.005, bz + 0.042), 0.012, 0.008, "SDT_Plastic", segments=16)
    cylinder_x("Coupler_WearIndicator", (0.052, by + 0.005, bz + 0.042), 0.008, 0.006, "SDT_LedGreen", segments=12)
    tube("Coupler_DrawTube", (0, by + 0.07, az), (0, tip.y + 0.02, az), 0.025, "SDT_Steel", segments=14)
    pleats = []
    y0, y1, n = by + 0.095, by + 0.185, 8
    for k in range(2 * n + 1):
        r = 0.031 if k % 2 == 0 else 0.042
        pleats.append((y0 + (y1 - y0) * k / (2 * n), r, az - r, az + r, 2.0))
    P.loft_y("Coupler_Bellows", pleats, "SDT_Rubber", segments=18)
    hy0, hy1 = y1, -2.88
    P.loft_y("Coupler_Housing", [
        (hy0, 0.046, az - 0.050, az + 0.050, 6.0), (hy0 + 0.02, 0.052, az - 0.055, az + 0.055, 6.0),
        (hy1 - 0.07, 0.052, az - 0.058, az + 0.058, 6.0), (hy1, 0.044, az - 0.040, az + 0.040, 5.0)], "SDT_Steel")
    for side, sx in (("L", 1), ("R", -1)):
        box(f"Coupler_Flange_{side}", sx * 0.050, sx * 0.058, -3.26, -2.96, az - 0.07, az + 0.06, "SDT_Steel")
        for k, fy in enumerate((-3.20, -3.02)):
            cylinder_x(f"Coupler_Bolt_{side}{k}", (sx * 0.062, fy, az), 0.011, 0.01, "SDT_Steel", segments=6)
    top = az + 0.058
    px, py = 0.0, -3.05
    box("Coupler_BrakePivot", px - 0.022, px + 0.022, py - 0.03, py + 0.03, top - 0.005, top + 0.03, "SDT_Steel")
    lever_end = Vector((px, -2.78, top + 0.19))
    tube("Coupler_BrakeLever", (px, py, top + 0.02), lever_end, 0.013, "SDT_Frame", segments=10)
    grip_dir = (lever_end - Vector((px, py, top + 0.02))).normalized()
    tube("Coupler_BrakeGrip", lever_end - grip_dir * 0.03, lever_end + grip_dir * 0.07, 0.019, "SDT_Rubber", segments=12)
    lever_mid = Vector((px, py, top + 0.02)).lerp(lever_end, 0.4)
    spring_foot = Vector((0.03, -3.24, az + 0.035))
    tube("Coupler_GasSpring", spring_foot, spring_foot.lerp(lever_mid, 0.6), 0.011, "SDT_Frame", segments=10)
    tube("Coupler_GasSpringRod", spring_foot.lerp(lever_mid, 0.6), lever_mid, 0.005, "SDT_Steel", segments=8)
    tube("Coupler_BrakeRod", (0, hy1 + 0.005, az - 0.01), (0, BASE_Y0 - 0.02, az - 0.01), 0.008, "SDT_Steel", segments=8)
    cable = P.hermite_path([(0.024, py + 0.02, top + 0.02), (0.06, -3.07, az + 0.04), (0.075, -3.22, az - 0.04),
                            (0.07, -3.37, bz - 0.07), (0.045, by + 0.07, bz - 0.095), (0.035, by + 0.045, bz - 0.10)],
                           samples=10)
    P.sweep("Coupler_BreakawayCable", cable, 0.0035, "SDT_Steel", segments=6)
    end = cable[-1]
    ring = [end + Vector((0, 0.018 * math.sin(a), -0.018 - 0.028 * math.cos(a)))
            for a in (2 * math.pi * k / 16 for k in range(17))]
    P.sweep("Coupler_Carabiner", ring, 0.0035, "SDT_Steel", segments=6)

    root = Vector((DRAWBAR_ROOT_X, BASE_Y0 + 0.40, DRAWBAR_Z))
    along = [root.lerp(tip, t) + Vector((-0.012, 0, 0.07)) for t in (0.3, 0.55, 0.8)]
    plug_a, plug_b = Vector((0.08, -3.30, bz - 0.005)), Vector((0.074, -3.39, bz - 0.04))
    wire = P.hermite_path([(0.42, BASE_Y0 + 0.03, DECK_TOP - 0.12)] + [tuple(p) for p in along] +
                          [(0.09, -3.18, bz + 0.02), tuple(plug_a)], samples=10)
    P.sweep("Coupler_13PinCable", wire, 0.006, "SDT_HoseBlack", segments=8)
    d = (plug_b - plug_a).normalized()
    tube("Coupler_13PinPlug", plug_a - d * 0.01, plug_b, 0.021, "SDT_Plastic", segments=14)
    tube("Coupler_13PinCap", plug_b, plug_b + d * 0.012, 0.024, "SDT_ChargerGrey", segments=14)
    box("Coupler_13PinDock", 0.40, 0.46, BASE_Y0 - 0.005, BASE_Y0 + 0.001, DECK_TOP - 0.16, DECK_TOP - 0.08,
        "SDT_Plastic")


def build_upper_structure():
    for side, sx in (("L", 1), ("R", -1)):
        px = sx * POST_X
        for i, py in enumerate(POST_Y):
            box(f"Post_{side}{i}", px - POST / 2, px + POST / 2, py - POST / 2, py + POST / 2,
                DECK_TOP, POST_TOP, "SDT_Frame")
        yf, yr = POST_Y[0], POST_Y[-1]
        plate_yz(f"Gusset_{side}_Front", px, 0.015, [(yf, POST_TOP - 0.45), (yf + 0.45, POST_TOP), (yf, POST_TOP)],
                 "SDT_Frame")
        plate_yz(f"Gusset_{side}_Rear", px, 0.015, [(yr, POST_TOP - 0.45), (yr, POST_TOP), (yr - 0.45, POST_TOP)],
                 "SDT_Frame")
        plate_yz(f"Knee_{side}", px, 0.015,
                 [(POST_Y[1] - 0.30, POST_TOP), (POST_Y[1], POST_TOP - 0.30), (POST_Y[1] + 0.30, POST_TOP)], "SDT_Frame")
        box(f"TopBeam_{side}", px - POST / 2, px + POST / 2, TOP_Y0, TOP_Y1, POST_TOP, POST_TOP + TOP_BEAM_H,
            "SDT_Frame")
    ox0, ox1, oy0, oy1, _ = chest_box()
    cross_y = []
    for py in [TOP_Y0 + 0.04] + POST_Y + [TOP_Y1 - REAR_CROSS_OFFSET]:
        if all(abs(py - q) > 0.08 for q in cross_y):          # sloupek v rohu desky (Middle) nese přední příčník
            cross_y.append(py)
    for i, py in enumerate(cross_y):
        y0, y1 = py - 0.035, py + 0.035
        if y1 > oy0 and y0 < oy1:
            # příčník, kterým prochází zapuštěná truhla nabíječky, se rozdělí na dva
            box(f"TopCross_{i}a", -POST_X, ox0, y0, y1, POST_TOP, POST_TOP + TOP_BEAM_H, "SDT_Frame")
            box(f"TopCross_{i}b", ox1, POST_X, y0, y1, POST_TOP, POST_TOP + TOP_BEAM_H, "SDT_Frame")
        else:
            box(f"TopCross_{i}", -POST_X, POST_X, y0, y1, POST_TOP, POST_TOP + TOP_BEAM_H, "SDT_Frame")
    hw = TOP_W / 2
    dz0, dz1 = TOP_SURF - TOP_PLATE, TOP_SURF
    box("TopDeck_Rear", -hw, hw, oy1, TOP_Y1, dz0, dz1, "SDT_TopDeck")
    box("TopDeck_Front", -hw, hw, TOP_Y0, oy0, dz0, dz1, "SDT_TopDeck")
    box("TopDeck_StripR", -hw, ox0, oy0, oy1, dz0, dz1, "SDT_TopDeck")
    box("TopDeck_StripL", ox1, hw, oy0, oy1, dz0, dz1, "SDT_TopDeck")
    for side, sx in (("L", 1), ("R", -1)):
        box(f"TopLip_{side}", sx * hw - sx * 0.035, sx * hw, TOP_Y0, TOP_Y1, TOP_SURF, TOP_SURF + 0.04, "SDT_Frame")
    lid_at_lip = oy0 - 0.012 < TOP_Y0 + 0.085       # otevřené víko sahá za pant o tloušťku nad lištu
    if lid_at_lip:
        # víko truhly se otevírá do svislé polohy a stojí v přední liště, ta má proto mezeru
        box("TopLip_FrontR", -hw, ox0 - 0.02, TOP_Y0, TOP_Y0 + 0.035, TOP_SURF, TOP_SURF + 0.04, "SDT_Frame")
        box("TopLip_FrontL", ox1 + 0.02, hw, TOP_Y0, TOP_Y0 + 0.035, TOP_SURF, TOP_SURF + 0.04, "SDT_Frame")
    else:
        box("TopLip_Front", -hw, hw, TOP_Y0, TOP_Y0 + 0.035, TOP_SURF, TOP_SURF + 0.04, "SDT_Frame")


def ladder_outward():
    """Znaménko osy X ven od vleku na straně žebříku (pravý bok = -1)."""
    return -1.0 if LADDER_SIDE_X < 0 else 1.0


def ladder_geometry():
    """(čep, spodek rozloženého žebříku, délka kolejnic od čepu dolů). Rozložený žebřík visí svisle dolů z čepu."""
    hinge = Vector((LADDER_SIDE_X, LADDER_HINGE_Y, LADDER_HINGE_Z))
    length = LADDER_HINGE_Z - LADDER_FOOT_Z
    return hinge, hinge - Vector((0.0, 0.0, length)), length


def ladder_fold_angle():
    """Natočení kloubu ladderHinge kolem osy X z rozložené (visí dolů, stav v i3d) do složené (leží od čepu po Y) polohy."""
    return LADDER_FOLD_DIR * math.pi / 2


def ladder_grab_fold_angle():
    """Natočení kloubu ladderGrab z rozložené (madla svisle nahoru, stav v i3d) do složené (leží po Y jako složený žebřík) polohy:
    opačný směr než žebřík, takže se oba sejdou vodorovně vedle sebe."""
    return -LADDER_FOLD_DIR * math.pi / 2


def build_ladder():
    """Sklopný žebřík v rozložené poloze (visí z čepu svisle dolů, to je stav v i3d): pevná konzola na boku horního nosníku s čepem,
    pod uzlem ladderHinge kolejnice, příčky, čep a horní příčník, pod uzlem ladderGrab madla nad horní deskou (vlastní kloub ve
    stejném čepu, sklápí se opačně než žebřík)."""
    hinge, foot, length = ladder_geometry()
    px, yc, zh = hinge.x, hinge.y, hinge.z
    sx = ladder_outward()
    x_out = sx * TOP_W / 2
    top_z = POST_TOP + TOP_BEAM_H - 0.02
    plate_t, boss_len = 0.012, 0.045
    x_plate = x_out + sx * plate_t
    x_boss = x_plate + sx * boss_len
    box("LadderMount_Plate", min(x_out, x_plate), max(x_out, x_plate), yc - 0.055, yc + 0.055, zh - 0.07, top_z, "SDT_Frame")
    cylinder_x("LadderMount_Boss", ((x_plate + x_boss) / 2, yc, zh), 0.032, boss_len, "SDT_Steel", segments=16)

    pivot = empty("ladderHinge", hinge)
    parts = []
    z_bot = zh - length
    for k, ky in (("Front", -1), ("Rear", 1)):
        y = yc + ky * LADDER_W / 2
        parts.append(tube(f"Ladder_Rail_{k}", (px, y, z_bot), (px, y, zh + LADDER_RAIL_R), LADDER_RAIL_R, "SDT_Steel", segments=10))
        parts.append(cylinder_z(f"Ladder_Foot_{k}", (px, y, z_bot - 0.01), 0.026, 0.02, "SDT_Rubber", segments=12))
    parts.append(tube("Ladder_TopBar", (px, yc - LADDER_W / 2, zh), (px, yc + LADDER_W / 2, zh), 0.016, "SDT_Steel", segments=10))
    parts.append(tube("Ladder_Pin", (x_boss + sx * 0.002, yc, zh), (px, yc, zh), 0.014, "SDT_Steel", segments=10))
    parts.append(cylinder_x("Ladder_Hub", (px, yc, zh), 0.034, 0.03, "SDT_Steel", segments=16))
    rungs = round(length / 0.28)
    for i in range(1, rungs + 1):
        z = z_bot + (zh - z_bot) * i / (rungs + 0.4)
        parts.append(box(f"Ladder_Rung_{i:02d}", px - 0.012, px + 0.012, yc - LADDER_W / 2, yc + LADDER_W / 2, z - 0.012,
                         z + 0.012, "SDT_TopDeck"))
    for o in parts:
        world = o.matrix_world.copy()
        o.parent = pivot
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_world = world

    grab = _group("ladderGrab", bpy.data.objects[ROOT_NAME], tuple(hinge))        # sourozenec kloubu žebříku, ne jeho dítě
    grab_top = TOP_SURF + LADDER_GRAB_UP
    gparts = []
    for k, ky in (("Front", -1), ("Rear", 1)):
        y = yc + ky * LADDER_GRAB_W / 2
        gparts.append(tube(f"Ladder_Grab_{k}", (px, y, zh + LADDER_GRAB_GAP), (px, y, grab_top), LADDER_GRAB_R, "SDT_Steel",
                           segments=10))
        gparts.append(tube(f"Ladder_GrabGrip_{k}", (px, y, grab_top - 0.25), (px, y, grab_top + 0.012), LADDER_GRAB_R + 0.004,
                           "SDT_Rubber", segments=10))
    for z_bar in (zh + LADDER_GRAB_GAP, grab_top - 0.45):
        gparts.append(tube(f"Ladder_GrabBar_{z_bar:.2f}", (px, yc - LADDER_GRAB_W / 2, z_bar), (px, yc + LADDER_GRAB_W / 2, z_bar),
                           0.014, "SDT_Steel", segments=10))
    for o in gparts:
        world = o.matrix_world.copy()
        o.parent = grab
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_world = world
    return pivot


def build_ladder_collision(pivot):
    """Kolize žebříku: kvádr v rovině žebříku, dítě kloubu (rozložený svislý, složený vodorovně podél boku).

    Končí LADDER_COL_MIN_Z nad zemí: dotek s terénem by vlek nadzvedával (kompoundní díl téže komponenty).
    """
    hinge, _, _ = ladder_geometry()
    half_w = LADDER_W / 2 + LADDER_RAIL_R + 0.04
    return _shape_box("colLadder", pivot, hinge.x - LADDER_COL_THICKNESS / 2, hinge.x + LADDER_COL_THICKNESS / 2, hinge.y - half_w,
                      hinge.y + half_w, LADDER_COL_MIN_Z, hinge.z, COL_VEHICLE, compoundChild=True, density=0.001)


def build_ladder_trigger(pivot):
    """Spouštěč lezení (hra mu přidá bit hráče a LadderTrigger): kvádr před žebříkem (vně vleku), v jeho kloubu; sahá
    LADDER_TRIGGER_OUT od žebříku ven a o kousek dovnitř přes okraj desky, nahoře přesahuje čep, ať hráč dolezne až na desku."""
    hinge, foot, length = ladder_geometry()
    sx = ladder_outward()
    half_w = LADDER_W / 2 + 0.05
    xa, xb = hinge.x + sx * LADDER_TRIGGER_OUT, hinge.x - sx * LADDER_TRIGGER_IN
    return _shape_box("ladderTrigger", pivot, min(xa, xb), max(xa, xb), hinge.y - half_w, hinge.y + half_w,
                      0.05, hinge.z + LADDER_TRIGGER_UP, COL_TRIGGER, kinematic=True, compound=True,
                      trigger=True)


def set_ladder(t):
    """Náhled animace: 0 = rozložený (visí svisle dolů, madla nahoru, stav v i3d), 1 = složený (žebřík i madla vodorovně po boku).
    Výsuvný žebřík Middle (build_slide_ladder, kloub má vlastnost sdt_tilt): 0 = vysunutý a vyklopený, 1 = zasunutý svisle."""
    hinge = bpy.data.objects["ladderHinge"]
    if "sdt_tilt" in hinge:
        (s0, s1), (r0, r1) = SLIDE_LADDER_TIME
        a, b = min(s0, r0), max(s1, r1)
        tt = a + (b - a) * t
        fs = min(max((tt - s0) / (s1 - s0), 0.0), 1.0)
        fr = min(max((tt - r0) / (r1 - r0), 0.0), 1.0)
        bpy.data.objects["ladderSlide"].location = Vector(hinge["sdt_slide"]) * fs
        hinge.rotation_euler.y = hinge["sdt_tilt"] * fr
        bpy.context.view_layer.update()
        return
    hinge.rotation_euler.x = ladder_fold_angle() * t
    bpy.data.objects["ladderGrab"].rotation_euler.x = ladder_grab_fold_angle() * t
    bpy.context.view_layer.update()


# --- výsuvný žebřík Middle (Pavel 2026-10-15, plachta): přední pravý roh mezi předním sloupkem a plachtou, bez madel ---
# Složený stojí svisle mezi sloupky a plachtou: horní díl visí háky na nosníku pod TopBeam, pata na opěrce na podélníku, spodní
# díl je zasunutý v něm (o SLIDE_LADDER_INSET blíž k vleku a užší). Rozložený: spodní díl sjede po horním dolů a žebřík se na
# hácích vyklopí, pata stojí na zemi. Model je rozložený (stav v i3d): ladderHinge (osa háků podél vleku) se při skládání
# naklopí do svislice, ladderSlide (spodní díl, dítě kloubu) vyjede nahoru. ladderGrab zůstává prázdný (export ho mapuje).
SLIDE_LADDER_X = -1.085                  # osa kolejnic složeného žebříku: mezi sloupky (-1,05) a plachtou (-1,13)
SLIDE_LADDER_Y = (-2.43, -2.10)          # kolejnice horního dílu: mezi předním sloupkem a kolem
SLIDE_LADDER_TOP = 2.11                  # osa háků; složený žebřík z 0,78 až sem
SLIDE_LADDER_SECTION = 1.33              # délka horního dílu
SLIDE_LADDER_FOOT_X = -1.70              # pata rozloženého na zemi ~0,6 m od plachty
SLIDE_LADDER_INSET = 0.035               # spodní díl za horním (k vleku) a v něm o tolik užší z každé strany
SLIDE_LADDER_RUNG = 0.28
SLIDE_LADDER_TIME = ((2.0, 2.4), (2.3, 2.6))   # s ve foldLadder: zasunutí spodního dílu, naklopení do svislice (plachta 2,6-3)


def slide_ladder_geometry():
    """(osa háků, směr dolů po rozloženém žebříku, normála ke vleku, délka po konec kolejnic spodního dílu, délka spodního dílu,
    naklopení kloubu do složené polohy kolem osy Y v radiánech)."""
    hinge = Vector((SLIDE_LADDER_X, sum(SLIDE_LADDER_Y) / 2, SLIDE_LADDER_TOP))
    a = (Vector((SLIDE_LADDER_FOOT_X, hinge.y, 0.0)) - hinge).normalized()
    n = Vector((-a.z, 0.0, a.x))
    foot_pad = 0.04
    length = -(hinge.z + n.z * SLIDE_LADDER_INSET) / a.z - foot_pad      # gumová patka konce spodního dílu stojí na zemi
    lower = SLIDE_LADDER_SECTION - 0.04                                 # složený spodní díl končí nad opěrkou paty
    return hinge, a, n, length, lower, -math.atan2(-a.x, -a.z)


def _ladder_frame(hinge, a, n):
    """Rámec žebříku: x = normála ke vleku, y = podél vleku, z = nahoru po žebříku; počátek v ose háků."""
    m = Matrix((n, Vector((0, 1, 0)), -a)).transposed().to_4x4()
    m.translation = hinge
    return m


def _ladder_shape(name, parent, frame, t0, t1, ya, yb, s0, s1, group_mask, **props):
    """Kvádr v rámci žebříku (t napříč ke vleku, y absolutně, s dolů po žebříku od háků) jako kolizní / spouštěcí tvar."""
    hy = frame.translation.y
    o = box(name, t0, t1, ya - hy, yb - hy, -s1, -s0, "SDT_Frame")
    o.matrix_world = frame @ o.matrix_world
    return _as_shape(o, parent, group_mask, **props)


def build_slide_ladder():
    """Výsuvný dvoudílný žebřík bez madel (viz SLIDE_LADDER_*), postavený rozložený. Pevný hákový nosník na deskách pod TopBeam
    a opěrka paty na pravém podélníku; pod ladderHinge horní díl s háky a kolize colLadder, spouštěč ladderTrigger; pod
    ladderSlide spodní díl s gumovými patkami a kolize colLadderLow. Do vlastností kloubů uloží řádky <part> animace foldLadder
    (export je vyplní do {{TARP_PARTS}}) a pro náhled set_ladder posuv (sdt_slide) a naklopení (sdt_tilt)."""
    vis = bpy.data.objects[ROOT_NAME]
    hinge_p, a, n, length, lower, tilt = slide_ladder_geometry()
    ls, ins = SLIDE_LADDER_SECTION, SLIDE_LADDER_INSET
    y0, y1 = SLIDE_LADDER_Y
    hx, hz = hinge_p.x, hinge_p.z
    x_face = -TOP_W / 2
    tube("LadderHookBar", (hx, y0 - 0.035, hz), (hx, y1 + 0.035, hz), 0.014, "SDT_Steel", segments=10)
    for k, y in enumerate((y0 - 0.045, y1 + 0.045)):
        box(f"LadderHookPlate{k}", hx - 0.02, x_face, y - 0.01, y + 0.01, hz - 0.03, POST_TOP - 0.012, "SDT_Frame")
        box(f"LadderHookTab{k}", x_face, x_face + 0.06, y - 0.01, y + 0.01, POST_TOP - 0.012, POST_TOP, "SDT_Frame")
    zs = hz - ls - 0.014                                                # opěrka pod patou složeného horního dílu
    box("LadderStopPlate", x_face - 0.012, x_face, y0 - 0.02, y1 + 0.02, DECK_TOP - 0.12, zs, "SDT_Frame")
    box("LadderStop", hx - 0.03, x_face, y0 - 0.02, y1 + 0.02, zs - 0.02, zs, "SDT_Frame")

    hinge = _group("ladderHinge", vis, tuple(hinge_p))
    slide = _group("ladderSlide", hinge, tuple(hinge_p))
    up, low = [], []
    for k, y in enumerate((y0, y1)):
        top = Vector((hx, y, hz))
        up.append(tube(f"Ladder_Rail_{k}", top, top + a * ls, 0.02, "SDT_Alu", segments=12))
        up.append(tube(f"Ladder_RailCap_{k}", top + a * ls, top + a * (ls + 0.012), 0.022, "SDT_Rubber", segments=12))
        up.append(box(f"Ladder_Hook_{k}", hx - 0.026, hx + 0.026, y - 0.016, y + 0.016, hz - 0.005, hz + 0.032, "SDT_Steel"))
        p0 = Vector((hx, y + (ins if k == 0 else -ins), hz)) + a * (length - lower) + n * ins
        low.append(tube(f"Ladder_LowRail_{k}", p0, p0 + a * lower, 0.017, "SDT_Alu", segments=12))
        low.append(tube(f"Ladder_Foot_{k}", p0 + a * lower, p0 + a * (lower + 0.04), 0.026, "SDT_Rubber", segments=12))
    # příčky: na spodním dílu od paty po SLIDE_LADDER_RUNG, na horním ve stejných místech rozloženého žebříku (v přesahu se kryjí)
    s = length - 0.10
    i = 0
    while s > length - lower + 0.03:
        p = hinge_p + a * s + n * ins
        low.append(tube(f"Ladder_LowRung_{i:02d}", (p.x, y0 + ins, p.z), (p.x, y1 - ins, p.z), 0.013, "SDT_Alu", segments=10))
        s -= SLIDE_LADDER_RUNG
        i += 1
    s = length - 0.10
    while s > ls - 0.05:
        s -= SLIDE_LADDER_RUNG
    i = 0
    while s > 0.08:
        p = hinge_p + a * s
        up.append(tube(f"Ladder_Rung_{i:02d}", (p.x, y0, p.z), (p.x, y1, p.z), 0.014, "SDT_Alu", segments=10))
        s -= SLIDE_LADDER_RUNG
        i += 1
    bpy.context.view_layer.update()
    for o in up:
        _set_parent(o, hinge, o.matrix_world.copy())
    for o in low:
        _set_parent(o, slide, o.matrix_world.copy())

    frame = _ladder_frame(hinge_p, a, n)
    child = dict(compoundChild=True, density=0.001)
    w = 0.06
    _ladder_shape("colLadder", hinge, frame, -0.05, 0.05, y0 - w, y1 + w, 0.0, ls, COL_VEHICLE, **child)
    s_ground = (hz - LADDER_COL_MIN_Z) / -a.z                            # kolize nesmí na zem (nadzvedávala by vlek)
    _ladder_shape("colLadderLow", slide, frame, ins - 0.05, ins + 0.05, y0 - w, y1 + w, length - lower, s_ground, COL_VEHICLE,
                  **child)
    _ladder_shape("ladderTrigger", hinge, frame, -LADDER_TRIGGER_OUT, LADDER_TRIGGER_IN, y0 - 0.05, y1 + 0.05,
                  -LADDER_TRIGGER_UP, length - 0.05, COL_TRIGGER, kinematic=True, compound=True, trigger=True)
    _group("ladderGrab", vis, tuple(hinge_p))

    shift = -a * (length - lower)                                       # spodní díl nahoru, v souřadnicích kloubu
    rot = _TO_I3D @ Matrix.Rotation(tilt, 4, "Y") @ _TO_I3D.inverted()
    e = [math.degrees(v) for v in rot.to_euler("XYZ")]
    (s0, s1), (r0, r1) = SLIDE_LADDER_TIME
    hinge["sdt_tilt"] = tilt
    hinge["sdt_slide"] = tuple(shift)
    hinge["sdt_fold_parts"] = (f'            <part node="ladderHinge" startTime="{r0:g}" endTime="{r1:g}" startRot="0 0 0" '
                               f'endRot="{P.i3d_fmt(e)}"/>')
    slide["sdt_mapped"] = 1
    slide["sdt_fold_parts"] = (f'            <part node="ladderSlide" startTime="{s0:g}" endTime="{s1:g}" startTrans="0 0 0" '
                               f'endTrans="{P.i3d_fmt(P.i3d_vec(shift))}"/>')
    print(f"žebřík: rozložený {length + 0.04:.2f} m, naklopení {math.degrees(-tilt):.1f}°, výsuv {length - lower:.3f} m")
    return hinge


def cabinet_level_h():
    _, _, h = T.CANISTER
    return h + 0.016 + 0.041 + CABINET_LEVEL_CLEARANCE   # tělo + hrdlo/víčko + rezerva do police dalšího patra


def build_canister_cabinet(prefix, x0, x1, y0, y1, z0, rows=CABINET_ROWS, cols=CABINET_COLS, levels=CABINET_LEVELS,
                            ceiling=None):
    """Skříň na kanystry: zadní stěna u y0 (směrem k nádrži), vrata u y1 (směrem ven z vleku, těsně za poslední
    řadou - viz cabinet_depth) - rolovací nahoru jako u garáže (Pavel 2026-10-09), aby nezavazela pevně uchycenému
    žebříku na boku, na který by narazila výklopná/posuvná boční vrata. V každém patře `rows` řad po `cols`
    kanystrech stojících na výšku (tvar T.build_canister), police jen nad přihrádkou - malá předsíňka před nimi (ke
    vratům) je volná od podlahy po strop. Uzly: toolboxCanister1..N (odspodu po patrech, v patře od zadní stěny k vratům, v řadě od x0 k x1),
    toolboxActivateNode (u vrat), {prefix}_Door (pivot vrat, scale po ose Y = výšce - viz SprayDroneToolbox.applyLid).
    `ceiling`: nad poslední patro až po tuto výšku jde plný strop bez polic/kanystrů, aby skříň opticky sahala až
    nahoru."""
    w, dv = CABINET_WALL, CABINET_DIV
    _, D, _ = T.CANISTER
    sd = D + 0.020                                  # hloubka slotu = kanystr + vůle
    level_h = cabinet_level_h()
    pitch = (x1 - x0 - 2 * w) / cols
    yw1 = y0 + w + rows * sd                        # zadní hrana přihrádek (u vrat dál k y1 je volná předsíňka)
    top_shelves = z0 + level_h * levels
    top = ceiling if (ceiling is not None and ceiling > top_shelves) else top_shelves
    mat, steel = "SDT_PaintDark", "SDT_Steel"
    box(f"{prefix}_Back", x0, x1, y0, y0 + w, z0, top, mat)
    box(f"{prefix}_Left", x1 - w, x1, y0, y1, z0, top, mat)
    box(f"{prefix}_Right", x0, x0 + w, y0, y1, z0, top, mat)
    box(f"{prefix}_Floor", x0, x1, y0, y1, z0, z0 + 0.018, mat)
    box(f"{prefix}_Roof", x0, x1, y0, y1, top - 0.018, top, mat)
    box(f"{prefix}_DoorRail", x0 - 0.004, x1 + 0.004, y1 - 0.03, y1 + 0.004, top_shelves - 0.03, top_shelves + 0.012,
        steel)
    centers = []
    for lvl in range(levels):
        zf = z0 + lvl * level_h
        box(f"{prefix}_Mat{lvl}", x0 + w, x1 - w, y0 + w, yw1 - w, zf + 0.018, zf + 0.024, "SDT_Rubber")
        if lvl > 0:
            box(f"{prefix}_Shelf{lvl}", x0 + w, x1 - w, y0 + w, yw1, zf, zf + 0.018, mat)
        for j in range(1, cols):
            dx = x0 + w + pitch * j
            box(f"{prefix}_Div{lvl}_{j}", dx - dv / 2, dx + dv / 2, y0 + w, yw1 - w, zf + 0.024,
                zf + level_h - 0.05, mat)
        for r in range(rows):
            ry0 = y0 + w + sd * r
            for c in range(cols):
                cx = x0 + w + pitch * (c + 0.5)
                centers.append(Vector((cx, ry0 + sd / 2, zf + 0.024)))
    act = P.empty("toolboxActivateNode", Vector(((x0 + x1) / 2, y1, (z0 + top_shelves) / 2)))
    act.empty_display_size = 0.10
    for k, c in enumerate(centers, 1):
        T.build_canister(f"toolboxCanister{k}", c)
    build_cabinet_door(prefix, x0, x1, y1, z0, top_shelves)
    build_cabinet_housing(prefix, x0, x1, y1, top_shelves, top)
    return len(centers)


def build_cabinet_door(prefix, x0, x1, y1, z0, ztop):
    """Rolovací vrata skříně: pozinkovaný plech (SDT_Steel) přes celý otvor (u y1, těsně za poslední řadou
    kanystrů), s vodorovnými lamelami jako u garážových vrat; pivot {prefix}_Door nahoře uprostřed -
    SprayDroneToolbox.applyLid mu mění scale.y mezi 1 (zavřeno) a téměř 0 (otevřeno), takže panel i lamely opticky
    mizí vzhůru pod DoorRail, jako by se navinuly (Pavel 2026-10-09: žádné výklopné/posuvné víko, zavazelo by
    pevnému žebříku na boku)."""
    t = 0.02
    rib = 0.004
    parts = [box(f"{prefix}_DoorPanel", x0, x1, y1 - t - rib, y1 - rib, z0, ztop, "SDT_Steel")]
    lamella_h = 0.12
    n = max(1, round((ztop - z0) / lamella_h))
    for i in range(1, n):
        zl = z0 + (ztop - z0) * i / n
        parts.append(box(f"{prefix}_DoorRib{i}", x0, x1, y1 - rib, y1, zl - 0.006, zl + 0.006,
                          "SDT_PaintDark"))
    pivot_pos = Vector(((x0 + x1) / 2, y1 - rib - t / 2, ztop))
    pivot = P.empty(f"{prefix}_Door", pivot_pos)
    pivot.empty_display_size = 0.08
    for o in parts:
        world = o.matrix_world.copy()
        o.parent = pivot
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_world = world
    return pivot


CABINET_HOUSING_MARGIN = 0.04       # panel vrat po vyjetí nahoru zůstane tolik pod stropem skříně


def cabinet_door_travel(top_shelves=None, top=None):
    """O kolik vyjede panel vrat nahoru do pouzdra nad otvorem (atribut doorTravel v <toolbox>): od horní hrany otvoru po strop
    skříně minus rezerva. Panel (dole zavěšený pivot Toolbox_Door nahoře uprostřed otvoru) se do pouzdra vejde jen svinutý
    (scale.y -> DOOR_OPEN_SCALE), v plné výšce by vyjel nad strop i plošinu."""
    z0 = DECK_TOP
    if top_shelves is None:
        top_shelves = z0 + cabinet_level_h() * CABINET_LEVELS
    if top is None:
        top = cabinet_ceiling()
    return max(0.0, top - top_shelves - CABINET_HOUSING_MARGIN)


def build_cabinet_housing(prefix, x0, x1, y1, top_shelves, top):
    """Pouzdro roletové schránky nad otvorem vrat: v dutině mezi horním patrem a stropem skříně (panel tam zajede po
    vyjetí nahoru) zakrývá dutinu čelní krycí plech s válcem (hřídel rolety) a bočními čepičkami; panel pod ním mizí. Nad
    DoorRail, pod stropem, na popisky vrat (z < top_shelves) nezasahuje."""
    gap = top - top_shelves
    if gap < 0.12:
        return
    mat, steel = "SDT_PaintDark", "SDT_Steel"
    zb, zt = top_shelves + 0.012, top - 0.002
    box(f"{prefix}_HousingFascia", x0 - 0.004, x1 + 0.004, y1 - 0.004, y1 + 0.012, zb, zt, mat)
    r = min(0.055, (zt - zb) / 2 - 0.01)
    zc = zb + r + 0.01
    yc = y1 + 0.012 + r * 0.45
    cylinder_x(f"{prefix}_HousingRoller", ((x0 + x1) / 2, yc, zc), r, x1 - x0 - 0.02, steel, segments=24)
    for k, xe in enumerate((x0 + 0.005, x1 - 0.005)):
        cylinder_x(f"{prefix}_HousingCap{k}", (xe, yc, zc), r + 0.012, 0.012, mat, segments=24)
    for i in (1, 2):
        zl = zb + (zt - zb) * (0.5 + 0.22 * i)
        if zl < zt - 0.02:
            box(f"{prefix}_HousingRib{i}", x0 + 0.02, x1 - 0.02, y1 + 0.012, y1 + 0.016, zl - 0.004, zl + 0.004, steel)


def cabinet_collisions(prefix, x0, x1, y0, y1, z0, rows=CABINET_ROWS, levels=CABINET_LEVELS, ceiling=None):
    """Celý půdorys (včetně předsíňky u vrat) jako plný kvádr - kanystry se neberou procházením dovnitř, ale
    dialogem/rukou, takže hráč tudy stejně procházet nemá (Pavel 2026-10-07: nastavit kolize všude)."""
    zt = z0 + cabinet_level_h() * levels
    if ceiling is not None and ceiling > zt:
        zt = ceiling
    return {
        f"col{prefix}Floor": (x0, x1, y0, y1, z0, zt),
    }


def build_equipment():
    z = DECK_TOP
    BT.build_main_tanks(z)                            # tankMain800 / 1000 / 1500 / 3000 / 5000, v i3d všechny viditelné
    ix, iy = T.INDUCTION_XY                           # ~50 l indukční
    T.build_induction_tank("Tank_Induction", ix, iy, z, T.INDUCTION_R, stand_h=T.INDUCTION_STAND_H,
                           cone_h=T.INDUCTION_CONE_H, body_h=T.INDUCTION_BODY_H)
    gen = G.build_generator(GEN_POS_MIDDLE, z, GEN_SOCKET)
    neck = P.empty("dieselNeckNode", Vector(gen["cap"]))
    neck.empty_display_size = 0.10
    px, py = T.PUMP_XY
    T.build_pump("Pump", px, py, z)
    tb_x0, tb_x1, _, _ = T.TOOLBOX_XY
    cy0, cy1 = cabinet_y_range()
    build_canister_cabinet("Toolbox", tb_x0, tb_x1, cy0, cy1, z, ceiling=cabinet_ceiling())
    build_hose_reel()


def build_hose_reel():
    """Modrý navíječ pod plošinou vpravo: buben s osou napříč, bočnice, konzoly vně bočnic (buben mezi nimi zůstává
    volný pro navinutou hadici) a otočný přívod na vnitřním konci osy."""
    rx, ry, rz = REEL
    cylinder_x("HoseReel_0_Drum", (rx, ry, rz), REEL_R, 0.20, "SDT_HoseBlue")
    for dx in (-0.11, 0.11):
        cylinder_x(f"HoseReel_0_Flange{dx:+.2f}", (rx + dx, ry, rz), REEL_R + 0.06, 0.015, "SDT_Frame")
    for side, xa, xb in (("Out", rx - 0.135, rx - 0.12), ("In", rx + 0.12, rx + 0.135)):
        box(f"HoseReel_0_Bracket{side}", xa, xb, ry - 0.04, ry + 0.04, rz - 0.04, TOP_SURF - TOP_PLATE, "SDT_Frame")
    tube("HoseReel_0_Axle", (rx - 0.14, ry, rz), (rx + 0.14, ry, rz), 0.02, "SDT_Steel", segments=12)


def _bbox_center(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return sum(pts, Vector()) / len(pts)


def drone_spec(prefix):
    key = next(k for k, p in DRONE_VARIANTS.items() if p == prefix)
    return key, D.SPECS[key]


def rotor_levels(prefix=DRONE_PREFIX):
    return drone_spec(prefix)[1]["levels"]


def drone_frame(prefix=DRONE_PREFIX):
    """Střed trupu (xy) a azimut nosu dronu (směr od trupu ke kamerám)."""
    body = _bbox_center(bpy.data.objects[prefix + "Body"])
    nose = _bbox_center(bpy.data.objects[prefix + "Nose"])
    return body.xy, math.atan2(nose.y - body.y, nose.x - body.x)


def _set_parent(obj, parent, world):
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_world = world


def _drone_empty(name, prefix=DRONE_PREFIX):
    e = bpy.data.objects.get(prefix + name)
    if e is None:
        e = bpy.data.objects.new(prefix + name, None)
        e.empty_display_type = "PLAIN_AXES"
        e.empty_display_size = 0.1
        bpy.data.collections[DRONE_COLLECTION].objects.link(e)
    return e


def build_drones():
    """Všechny tři drony znovu z build_drone.py (kolekce SprayDrone), složené, bez staré baterie v trupu,
    spodní listy složené ven podél ramene (dovnitř by vjely do trupu)."""
    coll = D.clear_collection()
    for key, prefix in DRONE_VARIANTS.items():
        D.build_drone(coll, name=prefix[:-1], spec=D.SPECS[key], arms_folded=1.0)
    bpy.context.view_layer.update()


def build_rotors(prefix=DRONE_PREFIX):
    """Každá vrtule (horní a spodní u každého motoru) pod vlastním uzlem na ose motoru, ať se dá točit.

    Uzel rotoru má natočení svého ramene, listy zůstanou na místě (počátek listu = střed náboje).
    """
    for i in range(1, 5):
        pivot = bpy.data.objects[f"{prefix}ArmPivot_{i}"]
        for level in rotor_levels(prefix):
            blades = [bpy.data.objects[f"{prefix}Blade_{i}{level}{b}"] for b in (0, 1)]
            rotor = _drone_empty(f"Rotor_{i}{level}", prefix)
            if rotor.parent is not pivot:
                rot = pivot.matrix_world.to_quaternion().to_matrix().to_4x4()
                _set_parent(rotor, pivot, Matrix.Translation(blades[0].matrix_world.translation) @ rot)
            for b in blades:
                if b.parent is not rotor:
                    _set_parent(b, rotor, b.matrix_world.copy())


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def drone_fold_parts(prefix=DRONE_PREFIX):
    """Natočení kloubů dronu složeno/rozloženo kolem svislé osy (radiány, lokálně k rodiči).

    Ramena: o kolik se kloub musí otočit, aby motor dosedl do rohu rozložené rozteče (build_drone.SPECS arm_span).
    Listy: každý se otočí tak, aby oba tvořily přímku napříč ramene (sdt_unfold_delta z build_drone.blade_fold_angles).
    Vrací [(uzel, složeno, rozloženo, druh)], druh "arm" nebo "blade".
    """
    bpy.context.view_layer.update()
    span = drone_spec(prefix)[1]["arm_span"]
    center, nose_az = drone_frame(prefix)
    fwd = Vector((math.cos(nose_az), math.sin(nose_az)))
    left = Vector((-fwd.y, fwd.x))
    parts = []
    for i in range(1, 5):
        pivot = bpy.data.objects[f"{prefix}ArmPivot_{i}"]
        p = pivot.matrix_world.translation.xy
        motor = _bbox_center(bpy.data.objects[f"{prefix}Motor_{i}"]).xy
        rel = p - center
        corner = (center + fwd * math.copysign(span[0] / 2, rel.dot(fwd))
                  + left * math.copysign(span[1] / 2, rel.dot(left)))
        delta = _wrap(math.atan2(*reversed(corner - p)) - math.atan2(*reversed(motor - p)))
        folded = pivot.matrix_local.to_euler().z
        parts.append((pivot.name, folded, folded + delta, "arm"))
        for level in rotor_levels(prefix):
            for b in (0, 1):
                blade = bpy.data.objects[f"{prefix}Blade_{i}{level}{b}"]
                bf = blade.matrix_local.to_euler().z
                parts.append((blade.name, bf, bf + blade["sdt_unfold_delta"], "blade"))
    return parts


def set_drone_unfold(t, parts=None, prefix=DRONE_PREFIX):
    """Náhled rozložení: 0 = složeno (stav v i3d), 1 = rozloženo."""
    for name, folded, unfolded, _ in parts or drone_fold_parts(prefix):
        bpy.data.objects[name].rotation_euler.z = folded + (unfolded - folded) * t
    bpy.context.view_layer.update()


def place_drone(prefix=DRONE_PREFIX):
    """Posadí dron doprostřed plošiny (střed heliportu), nosem po směru jízdy (-Y), s rameny složenými.

    Hierarchie pro hru: <prefix>Root (počátek = střed pod lyžinami, skript letu ho odpojí do světa)
    -> <prefix>Tilt (náklon za letu) -> díly, ramena (ArmPivot) -> rotory -> listy.
    Poloha se počítá z geometrie trupu, takže skript jde pouštět opakovaně.
    """
    # baterii dronu nahrazují modely battery1..5 (skript ji dává do <prefix>BatterySlot)
    for part in ("Battery", "BatteryLatch"):
        o = bpy.data.objects.get(prefix + part)
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)
    objs = P.drone_parts(prefix)
    if not objs:
        return
    # matrix_world dětí se po změně rodiče přepočítá až tady; bez toho se čtou staré polohy
    bpy.context.view_layer.update()
    tilt = _drone_empty("Tilt", prefix)
    for o in P.drone_parts(prefix):
        if o.parent is not None and (o.parent is tilt or o is tilt or not o.parent.name.startswith(prefix)):
            w = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = w
    bpy.context.view_layer.update()
    objs = P.drone_parts(prefix)
    roots = [o for o in objs if o.parent is None and o is not tilt]
    center, nose_az = drone_frame(prefix)
    floor = P.drone_footprint(objs).z
    target = Vector((0, DRONE_Y, TOP_SURF + 0.005))
    xf = (Matrix.Translation(target) @ Matrix.Rotation(-math.pi / 2 - nose_az, 4, "Z")
          @ Matrix.Translation(-Vector((center.x, center.y, floor))))
    for o in roots:
        o.matrix_world = xf @ o.matrix_world
    bpy.context.view_layer.update()
    build_rotors(prefix)
    bpy.context.view_layer.update()
    root = _group(prefix + "Root", bpy.data.objects[ROOT_NAME], tuple(target))
    _set_parent(tilt, root, Matrix.Translation(target + Vector((0, 0, DRONE_TILT_Z[drone_spec(prefix)[0]]))))
    for o in roots:
        _set_parent(o, tilt, o.matrix_world.copy())


def build_drone_leds(prefix=DRONE_PREFIX):
    """LED pod motorem každého ramene (dítě kloubu ramene, skládá se s ním) a malé bodové světlo pod ní.

    Objekty jsou v kolekci vleku, takže je každé sestavení smaže a postaví znovu.
    """
    bpy.context.view_layer.update()
    for i in range(1, 5):
        pivot = bpy.data.objects[f"{prefix}ArmPivot_{i}"]
        motor = bpy.data.objects[f"{prefix}Motor_{i}"]
        pts = [motor.matrix_world @ Vector(c) for c in motor.bound_box]
        cx, cy = sum(p.x for p in pts) / 8, sum(p.y for p in pts) / 8
        z1 = min(p.z for p in pts)
        sx, sy, sz = LED_SIZE
        # pod motorem může viset náboj nebo tryska, LED pak patří pod ně
        for under in ("HubBottom", "Nozzle"):
            ob = bpy.data.objects.get(f"{prefix}{under}_{i}")
            if ob is not None and ob.type == "MESH":
                for v in ob.data.vertices:
                    w = ob.matrix_world @ v.co
                    if abs(w.x - cx) < sx / 2 and abs(w.y - cy) < sy / 2:
                        z1 = min(z1, w.z)
        led = box(f"{prefix}Led_{i}", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, z1 - sz, z1, "SDT_NavLed")
        attr = led.data.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
        for d in attr.data:
            d.color_srgb = (*LED_COLORS[i], 1.0)
        led.data.color_attributes.render_color_index = 0
        _set_parent(led, pivot, led.matrix_world.copy())
        data = bpy.data.lights.get(f"{prefix}LedLight_{i}") or bpy.data.lights.new(f"{prefix}LedLight_{i}", "POINT")
        data.color = LED_COLORS[i]
        data.use_shadow = False
        data.use_custom_distance = True
        data.cutoff_distance = LED_LIGHT_RANGE
        light = bpy.data.objects.new(f"{prefix}LedLight_{i}", data)
        bpy.data.collections[COLLECTION_NAME].objects.link(light)
        _set_parent(light, led, Matrix.Translation((cx, cy, z1 - sz - 0.03)))


def clamp_open_angle(sx):
    """Otevřená čelist úchytu: sklopená nahoru a ven od lyžiny (kolem osy Y, podél lyžiny)."""
    return sx * math.radians(CLAMP_OPEN_DEG)


def build_drone_clamps(prefix=DRONE_PREFIX):
    """Úchyty lyžin dronu: pevný sloupek vedle lyžiny a čelist na závěsu (<prefix>ClampHinge_i), která ve skládací
    animaci vleku (po složení dronu) překlopí přes trubku lyžiny. V i3d je čelist otevřená (vlek rozložený).
    Celý úchyt je pod <prefix>Clamp_i (kvůli skrývání).
    """
    bpy.context.view_layer.update()
    names = []
    i = 0
    for side, sx in (("L", 1), ("R", -1)):
        skid = bpy.data.objects[f"{prefix}Skid_{side}"]
        pts = [skid.matrix_world @ Vector(c) for c in skid.bound_box]
        x_in, x_out = (min(p.x for p in pts), max(p.x for p in pts))[::sx]
        z_top = max(p.z for p in pts)
        hinge_x = x_out + sx * (CLAMP_GAP + CLAMP_POST / 2)
        hinge_z = z_top + CLAMP_JAW_T / 2 + 0.003
        for y in CLAMP_Y:
            i += 1
            y0, y1 = y - CLAMP_W / 2, y + CLAMP_W / 2
            clamp = empty(f"{prefix}Clamp_{i}", (hinge_x, y, TOP_SURF))
            post = box(f"{prefix}ClampPost_{i}", hinge_x - CLAMP_POST / 2, hinge_x + CLAMP_POST / 2, y0, y1, TOP_SURF,
                       hinge_z, "SDT_Frame")
            hinge = empty(f"{prefix}ClampHinge_{i}", (hinge_x, y, hinge_z))
            for o in (post, hinge):
                _set_parent(o, clamp, o.matrix_world.copy())
            tip = x_in - sx * 0.012
            parts = [
                box(f"{prefix}ClampJaw_{i}", min(hinge_x, tip), max(hinge_x, tip), y0, y1, hinge_z - CLAMP_JAW_T / 2,
                    hinge_z + CLAMP_JAW_T / 2, "SDT_LampAmber"),
                box(f"{prefix}ClampLip_{i}", min(tip, tip + sx * 0.012), max(tip, tip + sx * 0.012), y0, y1,
                    z_top - 0.045, hinge_z, "SDT_LampAmber"),
            ]
            for o in parts:
                _set_parent(o, hinge, o.matrix_world.copy())
            hinge.rotation_euler.y = clamp_open_angle(sx)
            names.append(hinge.name)
    bpy.context.view_layer.update()
    return names


def build_heliport():
    """Heliportové H v kruhu pod dronem: tenké vrstvy nad palubou, každá s vlastním decalLayer."""
    cx, cy, z = 0.0, DRONE_Y, TOP_SURF
    t = HELI_LAYER
    disk = cylinder_z("Heliport_Disk", (cx, cy, z + t / 2), HELI_R, t, "SDT_PaintDark", segments=64)
    ring = P.ring_z("Heliport_Ring", (cx, cy, z + 1.5 * t), *HELI_RING, t, "SDT_PaintWhite", segments=64)
    w, h, s = HELI_H
    z0, z1 = z + t, z + 2 * t
    marks = [
        box("Heliport_H_L", cx + w / 2 - s, cx + w / 2, cy - h / 2, cy + h / 2, z0, z1, "SDT_PaintWhite"),
        box("Heliport_H_R", cx - w / 2, cx - w / 2 + s, cy - h / 2, cy + h / 2, z0, z1, "SDT_PaintWhite"),
        box("Heliport_H_Bar", cx - w / 2 + s, cx + w / 2 - s, cy - s / 2, cy + s / 2, z0, z1, "SDT_PaintWhite"),
    ]
    for o, layer in [(disk, 1), (ring, 2)] + [(m, 2) for m in marks]:
        _physics(o, decalLayer=layer)


BATTERY_STAND = Matrix(((0, -1, 0, 0), (0, 0, -1, 0), (1, 0, 0, 0), (0, 0, 0, 1)))  # konektor dolů, rukojeť nahoru


def build_batteries():
    """Baterie battery<k> (kořen, pod ním meshe battery<k>S / M / L = DB800 / DB1560 / DB2160 se stejným rámcem slotu:
    konektor na dně šachty, střed tloušťky jako u M, viz P.battery). V i3d je viditelná jen M. Skript je přilinkuje
    k šachtám nabíječky (batterySlotDeck) nebo do dronu; do šachty je v Blenderu zavěsí attach_batteries()."""
    vis = bpy.data.objects[ROOT_NAME]
    for k in range(BATTERY_COUNT):
        meshes = [P.battery(f"battery{k + 1}{key}", P.BATTERY_SIZES[key]) for key in DRONE_VARIANTS]
        P.group(f"battery{k + 1}", meshes)


def attach_batteries():
    for k in range(1, BATTERY_COUNT + 1):
        slot = bpy.data.objects[f"batterySlotDeck{k}"]
        _set_parent(bpy.data.objects[f"battery{k}"], slot, slot.matrix_world.copy())


def chest_floor():
    """Podlaha truhly nabíječky: truhla je zapuštěná do vyříznutého otvoru v horní desce a okraj jejích stěn je
    CHEST_RIM nad deskou, víko tak leží v rovině desky."""
    depth = CHARGER_FEET + CHARGER_DOCK + 0.016 + P.BATTERY_SIZE[0] - CHARGER_EXPOSED + CHEST_LID_CLEAR
    return TOP_SURF + CHEST_RIM - depth


def charger_box():
    sx, sy = CHARGER_SHAFT
    w = CHARGER_WALL
    x0, x1 = CHARGER_CELL_X[0] - sx / 2 - w, CHARGER_CELL_X[-1] + sx / 2 + w
    y0, y1 = CHARGER_CELL_Y[0] - sy / 2 - w, CHARGER_CELL_Y[-1] + sy / 2 + w
    z0 = chest_floor() + CHARGER_FEET
    dock = z0 + CHARGER_DOCK
    top = dock + 0.016 + P.BATTERY_SIZE[0] - CHARGER_EXPOSED
    return x0, x1, y0, y1, z0, dock, top


def charger_leds(k, lx0, lx1, cy, z, pitch, length):
    """Pět diod šachty k na liště okraje (lx0..lx1 napříč, po Y kolem cy): Charger_Led_<k>_0 červená .. _4 zelená."""
    out = []
    for n, mat in enumerate(CHARGER_LED_MATS):
        ly = cy + (n - (len(CHARGER_LED_MATS) - 1) / 2) * pitch
        out.append(box(f"Charger_Led_{k}_{n}", lx0, lx1, ly - length / 2, ly + length / 2, z, z + 0.003, mat))
    return out


def build_charger():
    """Průmyslová nabíječka (styl DJI) v levém předním rohu horní paluby: šachty pro 6 baterií svisle, konektorem
    dolů na kontakty, nad hranu šachty vyčnívá jen horní čelo s rukojetí. batterySlotDeck1..6 jsou její děti."""
    vis = bpy.data.objects[ROOT_NAME]
    x0, x1, y0, y1, z0, dock, top = charger_box()
    w = CHARGER_WALL
    sx, sy = CHARGER_SHAFT
    charger = _group("batteryCharger", vis, ((x0 + x1) / 2, (y0 + y1) / 2, TOP_SURF))
    parts = []
    for fx in (x0 + 0.05, x1 - 0.05):
        for fy in (y0 + 0.05, y1 - 0.05):
            parts.append(cylinder_z(f"Charger_Foot_{fx:+.2f}_{fy:+.2f}", (fx, fy, chest_floor() + CHARGER_FEET / 2), 0.025,
                                    CHARGER_FEET, "SDT_Rubber", segments=12))
    parts += [
        box("Charger_Base", x0, x1, y0, y1, z0, dock, "SDT_ChargerGrey"),
        box("Charger_WallFront", x0, x1, y0, y0 + w, dock, top, "SDT_ChargerGrey"),
        box("Charger_WallRear", x0, x1, y1 - w, y1, dock, top, "SDT_ChargerGrey"),
        box("Charger_WallRight", x0, x0 + w, y0 + w, y1 - w, dock, top, "SDT_ChargerGrey"),
        box("Charger_WallLeft", x1 - w, x1, y0 + w, y1 - w, dock, top, "SDT_ChargerGrey"),
        box("Charger_DividerX", CHARGER_CELL_X[0] + sx / 2, CHARGER_CELL_X[1] - sx / 2, y0 + w, y1 - w, dock, top,
            "SDT_TankBlack"),
    ]
    for i in range(len(CHARGER_CELL_Y) - 1):
        ya, yb = CHARGER_CELL_Y[i] + sy / 2, CHARGER_CELL_Y[i + 1] - sy / 2
        parts.append(box(f"Charger_DividerY{i}", x0 + w, x1 - w, ya, yb, dock, top, "SDT_TankBlack"))
    rim = 0.006
    parts += [
        box("Charger_RimFront", x0, x1, y0, y0 + w, top, top + rim, "SDT_TankBlack"),
        box("Charger_RimRear", x0, x1, y1 - w, y1, top, top + rim, "SDT_TankBlack"),
        box("Charger_RimRight", x0, x0 + w, y0 + w, y1 - w, top, top + rim, "SDT_TankBlack"),
        box("Charger_RimLeft", x1 - w, x1, y0 + w, y1 - w, top, top + rim, "SDT_TankBlack"),
    ]
    cells = {(i, j): (CHARGER_CELL_X[i], CHARGER_CELL_Y[j]) for i in range(2) for j in range(3)}
    for k, cell in enumerate(CHARGER_SLOTS, 1):
        cx, cy = cells[cell]
        parts.append(box(f"Charger_Dock_{k}", cx - 0.07, cx + 0.07, cy - 0.035, cy + 0.035, dock, dock + 0.006,
                         "SDT_Steel"))
        lx0, lx1 = (x0 + 0.008, x0 + w - 0.008) if cell[0] == 0 else (x1 - w + 0.008, x1 - 0.008)
        parts += charger_leds(k, lx0, lx1, cy, top + rim, CHARGER_LED_PITCH, CHARGER_LED_LEN)
        _group(f"batterySlotDeck{k}", charger).matrix_world = (
            Matrix.Translation((cx, cy + P.BATTERY_SIZE[2] / 2, dock + 0.016 + P.BATTERY_SIZE[0] / 2)) @ BATTERY_STAND)

    def grille(tag, axis, face, lo, hi, sign):
        zs = [dock + 0.05 + 0.032 * n for n in range(int((top - dock - 0.16) / 0.032) + 1)]
        out = []
        for n, zc in enumerate(zs):
            a, b = (face, face + sign * 0.006) if sign > 0 else (face + sign * 0.006, face)
            if axis == "y":
                out.append(box(f"Charger_Vent{tag}_{n}", lo, hi, a, b, zc - 0.006, zc + 0.006, "SDT_Mesh"))
            else:
                out.append(box(f"Charger_Vent{tag}_{n}", a, b, lo, hi, zc - 0.006, zc + 0.006, "SDT_Mesh"))
        return out

    parts += grille("Front", "y", y0, x0 + 0.06, x1 - 0.06, -1)
    parts += grille("Right", "x", x0, y0 + 0.06, y1 - 0.06, -1)
    parts += grille("Left", "x", x1, y0 + 0.06, y1 - 0.06, 1)
    parts += [
        box("Charger_Label", x0 + 0.08, x1 - 0.08, y1, y1 + 0.003, dock + 0.12, dock + 0.24, "SDT_Decal"),
        box("Charger_LabelStripe", x0 + 0.08, x1 - 0.08, y1, y1 + 0.004, dock + 0.10, dock + 0.115, "SDT_GenOrange"),
    ]
    P.planar_uv(parts[-2], (x1 - 0.08, y1 + 0.003, dock + 0.12), (-1, 0, 0), (0, 0, 1), x1 - x0 - 0.16, 0.12,
                "chargerLabel")
    for side, fx, s in (("R", x0, -1), ("L", x1, 1)):
        hz = top - 0.06
        hy = (y0 + 0.08, y0 + 0.30)
        for n, py in enumerate(hy):
            parts.append(box(f"Charger_Handle{side}_Post{n}", min(fx, fx + s * 0.035), max(fx, fx + s * 0.035),
                             py - 0.012, py + 0.012, hz - 0.012, hz + 0.012, "SDT_TankBlack"))
        parts.append(tube(f"Charger_Handle{side}_Bar", (fx + s * 0.035, hy[0] - 0.012, hz), (fx + s * 0.035, hy[1] + 0.012, hz),
                          0.012, "SDT_Rubber", segments=10))
    for o in parts:
        _set_parent(o, charger, o.matrix_world.copy())
    return charger


def chest_box():
    x0, x1, y0, y1, _, _, top = charger_box()
    m = CHEST_WALL
    return x0 - CHEST_GAP_X - m, x1 + CHEST_GAP_X + m, y0 - CHEST_GAP_Y - m, y1 + CHEST_GAP_Y + m, top + CHEST_LID_CLEAR


def build_charger_chest():
    """Truhla nabíječky na horní palubě vpředu vlevo: čtyři stěny kolem nabíječky, víko na předním závěsu
    (chargerLid, v i3d otevřené = rozložený vlek) a napájecí zásuvka na vnější stěně vlevo."""
    vis = bpy.data.objects[ROOT_NAME]
    ox0, ox1, oy0, oy1, zw = chest_box()
    m, t = CHEST_WALL, CHEST_LID_T
    mat = "SDT_PaintDark"
    cx = (ox0 + ox1) / 2
    fl = chest_floor()
    box("Chest_Floor", ox0, ox1, oy0, oy1, fl - m, fl, mat)
    box("Chest_WallFront", ox0, ox1, oy0, oy0 + m, fl - m, zw, mat)
    box("Chest_WallRear", ox0, ox1, oy1 - m, oy1, fl - m, zw, mat)
    box("Chest_WallRight", ox0, ox0 + m, oy0 + m, oy1 - m, fl - m, zw, mat)
    box("Chest_WallLeft", ox1 - m, ox1, oy0 + m, oy1 - m, fl - m, zw, mat)
    sz = fl + CHARGER_SOCKET_Z
    box("Chest_Socket", ox1, ox1 + 0.02, CHARGER_SOCKET_Y - 0.035, CHARGER_SOCKET_Y + 0.035, sz - 0.035, sz + 0.035,
        "SDT_TankBlack")
    for n, lx in enumerate((cx - 0.25, cx + 0.25)):
        box(f"Chest_LatchBase{n}", lx - 0.03, lx + 0.03, oy1, oy1 + 0.012, zw - 0.015, zw - 0.005, "SDT_Steel")

    hy = oy0 - 0.012
    lid = [
        box("Chest_Lid", ox0 - 0.012, ox1 + 0.012, hy, oy1 + 0.012, zw, zw + t, mat),
        box("Chest_LidLipLeft", ox1, ox1 + 0.012, oy0 + m, oy1 + 0.012, zw - 0.012, zw, mat),
        box("Chest_LidLipRight", ox0 - 0.012, ox0, oy0 + m, oy1 + 0.012, zw - 0.012, zw, mat),
        box("Chest_LidLipRear", ox0 - 0.012, ox1 + 0.012, oy1, oy1 + 0.012, zw - 0.012, zw, mat),
        box("Chest_LidStripe", ox0 + 0.05, ox1 - 0.05, hy + 0.05, hy + 0.075, zw + t, zw + t + 0.002, "SDT_GenOrange"),
        tube("Chest_LidHandle", (cx - 0.10, oy1 + 0.045, zw + t / 2), (cx + 0.10, oy1 + 0.045, zw + t / 2), 0.01,
             "SDT_Steel", segments=10),
        box("Chest_LidHandlePostA", cx - 0.105, cx - 0.095, oy1 + 0.012, oy1 + 0.045, zw + t / 2 - 0.01,
            zw + t / 2 + 0.01, "SDT_Steel"),
        box("Chest_LidHandlePostB", cx + 0.095, cx + 0.105, oy1 + 0.012, oy1 + 0.045, zw + t / 2 - 0.01,
            zw + t / 2 + 0.01, "SDT_Steel"),
    ]
    for n, lx in enumerate((cx - 0.25, cx + 0.25)):
        lid.append(box(f"Chest_LatchTongue{n}", lx - 0.02, lx + 0.02, oy1 + 0.012, oy1 + 0.02, zw - 0.015, zw + t,
                       "SDT_Steel"))
    for n, lx in enumerate((cx - 0.28, cx + 0.28)):
        lid.append(tube(f"Chest_Hinge{n}", (lx - 0.05, hy, zw + 0.004), (lx + 0.05, hy, zw + 0.004), 0.014, "SDT_Steel",
                        segments=10))
    pivot = _group("chargerLid", vis, (cx, hy, zw))
    for o in lid:
        _set_parent(o, pivot, o.matrix_world.copy())
    pivot.rotation_euler.x = math.radians(CHEST_OPEN_DEG)
    bpy.context.view_layer.update()
    return pivot


def _rounded_polyline(pts, r=0.06, steps=6):
    """Lomená čára se zaoblenými rohy (kvadratická Bézierova křivka v každém rohu, poloměr nejvýš r) pro kabely vedené po rámu."""
    pts = [Vector(p) for p in pts]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p, a, b = pts[i], pts[i - 1], pts[i + 1]
        d = min(r, (a - p).length / 2, (b - p).length / 2)
        u, v = p + (a - p).normalized() * d, p + (b - p).normalized() * d
        for k in range(steps + 1):
            t = k / steps
            out.append((1 - t) ** 2 * u + 2 * t * (1 - t) * p + t ** 2 * v)
    out.append(pts[-1])
    return out


CABLE_RUN_X = POST_X - POST / 2 + 0.015       # kabel po zadní straně předního sloupku Post_L0 (osa uvnitř šířky sloupku)
CABLE_RUN_Y = POST_Y[0] + POST / 2 + CABLE_R + 0.004


def charger_cable_points():
    """Ze zásuvky truhly pod lem horní desky, po zadní straně sloupku Post_L0 dolů a po palubě dozadu k zásuvce centrály."""
    ox1, sy, sz = chest_box()[1], CHARGER_SOCKET_Y, chest_floor() + CHARGER_SOCKET_Z
    gx, gy, gz = GEN_SOCKET
    x, y = CABLE_RUN_X, CABLE_RUN_Y
    return [(ox1 + 0.05, sy, sz), (x, sy - 0.04, sz + 0.046), (x, sy - 0.11, POST_TOP - 0.07), (x, y + 0.075, POST_TOP - 0.07),
            (x, y + 0.015, POST_TOP - 0.12), (x, y, POST_TOP - 0.23), (x, y, 1.35), (x - 0.01, y + 0.035, 1.20),
            (x - 0.03, y + 0.175, 1.16), (gx + 0.065, gy - 0.15, gz), (gx + 0.055, gy, gz)]


def build_charger_cable():
    """Napájecí kabel truhla nabíječky → elektrocentrála, napevno (vidět i složený): ze zásuvky na levé stěně truhly pod lem
    horní desky, po zadní straně předního sloupku Post_L0 dolů (příchytky na sloupku a pod nosníkem) a k zásuvce na boku centrály.
    Zástrčky na obou koncích a příchytky jsou jeho děti. Jen vizuál."""
    path = P.hermite_path(charger_cable_points(), samples=12)
    cable = P.sweep("chargerCable", path, CABLE_R, "SDT_HoseBlack", segments=10)
    ox1, sy, sz = chest_box()[1], CHARGER_SOCKET_Y, chest_floor() + CHARGER_SOCKET_Z
    gx, gy, gz = GEN_SOCKET
    x, y = CABLE_RUN_X, CABLE_RUN_Y
    py1 = POST_Y[0] + POST / 2
    parts = [
        tube("Charger_Plug", (ox1 + 0.02, sy, sz), (ox1 + 0.055, sy, sz), 0.018, "SDT_Rubber", segments=12,
             radius_end=0.012),
        tube("Gen_0_ChargePlug", (gx + 0.015, gy, gz), (gx + 0.05, gy, gz), 0.018, "SDT_Rubber", segments=12,
             radius_end=0.012),
    ]
    # příchytky: objímky přes kabel přišroubované na zadní stěnu sloupku a jedna pod horním nosníkem
    for n, z in enumerate((1.45, 1.80, 2.10)):
        parts.append(box(f"Charger_CableClip{n}", x - 0.015, x + 0.015, py1 - 0.003, y + CABLE_R + 0.004, z - 0.012, z + 0.012,
                         "SDT_Steel"))
    cy = (sy - 0.11 + y + 0.075) / 2
    parts.append(box("Charger_CableClipTop", x - 0.014, x + 0.014, cy - 0.012, cy + 0.012, POST_TOP - 0.07 - CABLE_R - 0.004,
                     POST_TOP + 0.003, "SDT_Steel"))
    for o in parts:
        _set_parent(o, cable, o.matrix_world.copy())
    return cable, P.path_length(path)


# ------------------------------------------------------------- uložení retranslačních tyčí a pevný displej plánovače
# Tyč uložená na vleku: relaySlot<i> je prázdný uzel v ose uložené tyče (natočení jako vlek, tyč leží podél osy Y Blenderu =
# i3d Z), pod ním relaySlot<i>_pole je zjednodušená maketa složené tyče (skript ji skrývá podle obsazení slotu). U-třmeny
# s deskou na držáku vleku jsou pevné a vidět pořád.
RELAY_POLE_LEN = 1.45
RELAY_CLAMP_R = 0.083             # osa drátu U-třmenu od osy tyče
RELAY_CLAMP_WIRE = 0.008
RELAY_HEAD_LEN = 0.33             # od čela tyče: skříňka rádia a bateriový box (třmeny musí být dál)
# displej plánovače (rám z gumy, obrazovka s logem designu); plannerScreenNode je uprostřed obrazovky, i3d +Z míří ven z displeje
PLANNER_W, PLANNER_H, PLANNER_T = 0.28, 0.20, 0.04
# Middle (2026-10-15, plachta): dvě tyče svisle hlavou nahoru v jedné řadě ve skříňce vlevo mezi elektrocentrálou a nádrží
# (pod plachtou, z boku otevřená); displej uvnitř hned za předním levým sloupkem Post_L0, obrazovkou ven
RELAY_CABINET = (0.80, 0.965, -0.80, -0.42, DECK_TOP, 2.30)      # x0, x1 (otevřený bok), y0, y1, z0, z1
RELAY_SLOTS_MIDDLE = [(1, 0.8825, -0.705), (2, 0.8825, -0.515)]   # i, x, y osy tyče
RELAY_POLE_Z0 = DECK_TOP + 0.04                                  # pata tyče na dně skříňky
PLANNER_MIDDLE = ((1.017, -2.26, 1.50), 0.0)      # střed displeje, náklon obrazovky nahoru (°)


def _under_node(obj, node):
    """Mesh s vrcholy ve světě (počátek scény, např. z P.merge) zavěsí pod node s počátkem v node."""
    m = node.matrix_world.copy()
    obj.data.transform(m.inverted() @ obj.matrix_world)
    obj.parent = node
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_basis = Matrix.Identity(4)
    return obj


def relay_pole_mockup(i, x, y0, y1, z, head_front, scale=1.0):
    """Ležatá maketa uložené tyče podél vleku (y0..y1 ve výšce z, čelo vpředu / vzadu) přes P.relay_pole_mockup, který umí
    i svislou tyč hlavou nahoru: P.relay_pole_mockup(i, vis, head=(x, y, z_nahoře), tail=(x, y, z_dole))."""
    head, tail = ((x, y0, z), (x, y1, z)) if head_front else ((x, y1, z), (x, y0, z))
    return P.relay_pole_mockup(i, bpy.data.objects[ROOT_NAME], head, tail, scale)


def relay_clamp(name, x, y, z, side, mount_x, r=RELAY_CLAMP_R, wire=RELAY_CLAMP_WIRE, plate_h=0.12):
    """Pevný U-třmen kolem uložené tyče (osa podél Y) otevřený k vleku; ramena končí v desce na ploše mount_x (deska jde od ní
    12 mm ven). side = +1 tyč vlevo (+X), -1 vpravo."""
    face = mount_x + side * 0.012
    a45 = math.radians(135)
    pts = [Vector((face, y, z + r * math.sin(a45)))]
    for k in range(19):
        a = math.radians(135 - 15 * k)
        pts.append(Vector((x + side * r * math.cos(a), y, z + r * math.sin(a))))
    pts.append(Vector((face, y, z - r * math.sin(a45))))
    u = P.sweep(name, pts, wire, "SDT_Steel", segments=8)
    xa, xb = sorted((mount_x, face))
    plate = box(name + "_Plate", xa, xb, y - 0.03, y + 0.03, z - plate_h / 2, z + plate_h / 2, "SDT_Frame")
    nuts = [cylinder_x(f"{name}_Nut{n}", (face + side * 0.004, y, z + dz), 0.008, 0.008, "SDT_Steel", segments=6)
            for n, dz in enumerate((r * math.sin(a45), -r * math.sin(a45)))]
    return [u, plate] + nuts


def planner_display(center, normal, up):
    """Pevný displej plánovače: gumový rám se zesílenými rohy a lemem kolem obrazovky, na zadní straně patka pro držák.
    plannerDisplay nese rám a tmavou (vypnutou) obrazovku; svítící obsah (podsvícená plocha s polepy designu brand_<KEY>_planner)
    je samostatný mesh plannerScreenOn 1 mm nad ní, skript ho skrytím zhasne.
    Vrací (mesh plannerDisplay, uzel plannerScreenNode, střed zadní patky)."""
    vis = bpy.data.objects[ROOT_NAME]
    n = Vector(normal).normalized()
    u = Vector(up)
    u = (u - n * u.dot(n)).normalized()
    w = u.cross(n)
    frame = Matrix((w, u, n)).transposed().to_4x4()
    frame.translation = Vector(center)
    hw, hh, t = PLANNER_W / 2, PLANNER_H / 2, PLANNER_T / 2
    sw, sh, zs = hw - 0.022, hh - 0.022, t - 0.0015
    lip = hw - 0.008                                 # vnější hrana lemu = začátek zkosení těla
    lip_y = hh - 0.008
    parts = [P.chamfer_box("Planner_Body", -hw, hw, -hh, hh, -t, t - 0.002, "SDT_Rubber", 0.008),
             box("Planner_Screen", -sw, sw, -sh, sh, t - 0.0025, zs, "SDT_ScreenOff"),
             box("Planner_LipL", -lip, -sw, -lip_y, lip_y, t - 0.003, t + 0.002, "SDT_Rubber"),
             box("Planner_LipR", sw, lip, -lip_y, lip_y, t - 0.003, t + 0.002, "SDT_Rubber"),
             box("Planner_LipB", -sw, sw, -lip_y, -sh, t - 0.003, t + 0.002, "SDT_Rubber"),
             box("Planner_LipT", -sw, sw, sh, lip_y, t - 0.003, t + 0.002, "SDT_Rubber"),
             box("Planner_Mount", -0.05, 0.05, -0.05, 0.05, -t - 0.02, -t, "SDT_PaintDark")]
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0, x1 = sorted((sx * (hw - 0.035), sx * (hw + 0.005)))
            y0, y1 = sorted((sy * (hh - 0.035), sy * (hh + 0.005)))
            parts.append(P.chamfer_box(f"Planner_Corner{sx}{sy}", x0, x1, y0, y1, -t - 0.003, t + 0.002, "SDT_Rubber", 0.006))
    on = [box("Planner_Backlight", -sw, sw, -sh, sh, zs + 0.001, zs + 0.0013, "SDT_Screen")]
    for o in parts + on:
        o.matrix_world = frame @ o.matrix_world
    disp = P.merge("plannerDisplay", parts)
    screen_on = P.merge("plannerScreenOn", on)
    # úvodní obrazovka: lockup zvoleného designu (znak + název) a pod ním pruh v barvě designu; polepy visí pod
    # plannerScreenOn, takže zhasínají s obrazovkou, a design je přepíná přes objectChange jako ostatní polepy
    lz = zs + 0.0013
    P.brand_decal_set("planner", "lockupOnDark", frame @ Vector((0.0, 0.012, lz)), n, u, 2 * sw - 0.006,
                      parent=screen_on, offset=0.0008)
    P.brand_decal_set("planner", "stripe", frame @ Vector((0.0, -sh + 0.022, lz)), n, u, 2 * sw * 0.6, 0.005,
                      parent=screen_on, offset=0.0008, tag="Bar")
    node = _group("plannerScreenNode", vis, (0, 0, 0))
    m = Matrix((w, -n, u)).transposed().to_4x4()
    m.translation = frame @ Vector((0, 0, zs))
    node.matrix_world = m
    return disp, node, frame @ Vector((0, 0, -t - 0.02))


def build_relay_holders():
    """Middle: skříňka na dvě složené tyče relé vlevo mezi elektrocentrálou a nádrží (RELAY_CABINET): zadní stěna u vleku,
    boky, strop, dno, přepážka mezi tyčemi a dvě vodorovné lišty s kolébkami; tyče stojí svisle hlavou nahoru v jedné řadě po Y.
    Ven z vleku otevřená (bez dvířek, kryje ji plachta jako u Maxu). Kolize colRelayCabinet je v equipment_collisions."""
    vis = bpy.data.objects[ROOT_NAME]
    x0, x1, y0, y1, z0, z1 = RELAY_CABINET
    t, mat = 0.012, "SDT_ChargerGrey"
    box("RelayCab_Back", x0, x0 + t, y0, y1, z0, z1, mat)
    box("RelayCab_SideF", x0, x1, y0, y0 + t, z0, z1, mat)
    box("RelayCab_SideR", x0, x1, y1 - t, y1, z0, z1, mat)
    box("RelayCab_Top", x0, x1, y0, y1, z1 - t, z1, mat)
    box("RelayCab_Floor", x0, x1, y0, y1, z0, z0 + 0.03, mat)
    ym = (RELAY_SLOTS_MIDDLE[0][2] + RELAY_SLOTS_MIDDLE[1][2]) / 2
    box("RelayCab_Divider", x0 + t, x1 - 0.03, ym - 0.005, ym + 0.005, z0 + 0.03, z1 - t, mat)
    for k, z in enumerate((1.05, 1.95)):
        box(f"RelayCab_Bar{k}", x0 + t, x0 + 0.026, y0 + t, y1 - t, z - 0.02, z + 0.02, "SDT_Rubber")
    for i, x, y in RELAY_SLOTS_MIDDLE:
        P.relay_pole_mockup(i, vis, (x, y, RELAY_POLE_Z0 + RELAY_POLE_LEN), (x, y, RELAY_POLE_Z0))


def build_planner_tablet():
    """Middle: displej plánovače uvnitř hned za předním levým sloupkem Post_L0, obrazovka ven (+X) bez náklonu; drží ho dvě
    ploché příložky ze zadní plochy sloupku přes boční hranu rámu displeje."""
    (cx, cy, cz), tilt = PLANNER_MIDDLE
    a = math.radians(tilt)
    disp, node, back = planner_display((cx, cy, cz), (math.cos(a), 0, math.sin(a)), (-math.sin(a), 0, math.cos(a)))
    pts = [disp.matrix_world @ Vector(c) for c in disp.bound_box]
    dy0, dx1 = min(p.y for p in pts), max(p.x for p in pts)
    py1 = POST_Y[0] + POST / 2
    parts = []
    for k, z in enumerate((cz - 0.08, cz + 0.08)):
        parts.append(box(f"Planner_Clip{k}", cx - 0.017, dx1 + 0.001, py1, dy0 + 0.03, z - 0.012, z + 0.012, "SDT_Steel"))
        parts.append(box(f"Planner_ClipLip{k}", dx1 - 0.003, dx1 + 0.004, dy0 - 0.002, dy0 + 0.024, z - 0.012, z + 0.012,
                         "SDT_Steel"))
        parts.append(cylinder_z(f"Planner_ClipBolt{k}", (cx + 0.004, py1 + 0.025, z + 0.014), 0.007, 0.004, "SDT_Steel",
                                segments=6))
    P.merge("plannerMount", parts)
    return node


def build_drone_service_parts(prefix=DRONE_PREFIX):
    """Na trupu dronu: lůžko baterie (<prefix>BatterySlot) a plnicí hrdlo (<prefix>FillPort, +Z i3d míří do hrdla).

    Slot je posunutý tak, aby baterie jeho velikosti (rámec slotu = rámec M, viz P.battery) ležela na lůžku
    konektorem k zásuvce (-X) a uprostřed lůžka.
    """
    key, _ = drone_spec(prefix)
    tilt = bpy.data.objects[prefix + "Tilt"]
    body = bpy.data.objects[prefix + "Body"]
    top = max((body.matrix_world @ Vector(c)).z for c in body.bound_box)
    size = P.BATTERY_SIZES[key]
    lx, ly = size[0] / 2, size[1] / 2
    bx, by = DRONE_BATTERY[key]
    # šachta zapuštěná do hřbetu trupu a otevřená dozadu (baterie se zasouvá zezadu), z trupu čnívá jen její horní hrana
    depth = size[2] - 0.015
    seat = top - depth
    x0, x1, y0, y1 = bx - lx - 0.006, bx + lx + 0.006, by - ly - 0.006, by + ly + 0.006
    cutter = box(prefix + "BayCut", x0, x1, y0, y1 + 0.6, seat, top + 0.2, "Drone_Grey")
    mod = body.modifiers.new("bay", "BOOLEAN")
    mod.operation, mod.object, mod.solver = "DIFFERENCE", cutter, "EXACT"
    with bpy.context.temp_override(object=body, active_object=body, selected_objects=[body]):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    data = cutter.data
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.data.meshes.remove(data)
    parts = [
        box(f"{prefix}BatteryBay", x0, x1, y0, y1, seat - 0.004, seat + 0.002, "SDT_TankBlack"),
        box(f"{prefix}BatteryBayContacts", x0 + 0.002, x0 + 0.006, by - 0.05, by + 0.05, seat + 0.035, seat + 0.08,
            "SDT_Steel"),
    ]
    px, py = DRONE_FILL_PORT[key]
    port_top = top + 0.046        # o 4 mm níž než dřív: složený list vrtule S (nad hřbetem) by jinak zajel do jantarového lemu
    parts += N.fill_port_parts(prefix, px, py, top, port_top)
    for o in parts:
        _set_parent(o, tilt, o.matrix_world.copy())
    dx, dz = P.battery_frame_offset(size)
    _group(prefix + "BatterySlot", tilt, (bx - dx, by, seat - dz))
    i3d_rot_node(prefix + "FillPort", tilt, (px, py, port_top), (90, 0, 0))


def _aim(d, up=None):
    """Natočení, při kterém lokální -Y Blenderu (= +Z i3d) míří po d a lokální +Z (= +Y i3d) po up (výchozí svisle)."""
    if up is None:
        return d.normalized().to_track_quat("-Y", "Z").to_matrix().to_4x4()
    y = -d.normalized()
    z = (up - y * up.dot(y)).normalized()
    m = Matrix((y.cross(z), y, z)).transposed().to_4x4()
    return m


def nozzle_park_matrix():
    """Klidová poloha koncovky: leží na boku, "nahoře" koncovky (spoušť opačně) míří dopředu k přednímu okraji desky,
    stejně jako nahoře uzlu plnicího hrdla dronu - koncovka se k hrdlu jen sklápí kolem vodorovné osy."""
    d = Vector(HOSE_PARK_DIR).normalized()
    up = d.cross(Vector((0, 0, 1)))
    return Matrix.Translation(Vector(HOSE_PARK_TIP) + Vector((0, 0, NOZZLE_LIFT))) @ _aim(d, up)


def hose_inlet():
    """Konec hadice v přívodu klidové koncovky (svět) a směr, kterým do něj hadice vchází."""
    m = nozzle_park_matrix()
    return m @ N.INLET_END, -(m.to_3x3() @ N.INLET_OUT)


def hose_lay_points():
    """Start, Lay1..Lay8 (Lay6 = začátek rovného nájezdu, Lay7 = konec hadice v přívodu, Lay8 = špička koncovky v klidu)
    a směr, kterým hadice vchází do přívodu."""
    end, din = hose_inlet()
    lay = [Vector(p) for p in HOSE_LAY]
    return Vector(HOSE_START), lay + [end - din * HOSE_LEAD, end, nozzle_park_matrix().translation], din


def hose_rest_path():
    """Klidová křivka hadice stejně jako v Lua (SprayDroneService.getRestLine): Catmull-Rom přes body, v lokálním minimu
    výšky vodorovná tečna (hadice nejde deskou), posledních HOSE_LEAD m rovně v ose přívodu koncovky."""
    start, lay, d = hose_lay_points()
    pts = [start] + lay[:-1]
    n = len(pts)
    tangents = {n - 2: d, n - 1: d}
    for i in range(1, n - 2):
        if pts[i].z <= pts[i - 1].z + 1e-4 and pts[i].z <= pts[i + 1].z + 1e-4:
            t = (pts[i + 1] - pts[i - 1]) / 2
            tangents[i] = Vector((t.x, t.y, 0.0))
    return P.hermite_path(pts, tangents=tangents, samples=16)


def build_hose_reel_parts():
    """Hadice namotaná na modrém bubnu (fillHoseCoil), pevný úsek z bubnu svisle nahoru vnitřkem do průchodky v horní desce
    (gumová průchodka nahoře, vodicí kroužek pod deskou s ramenem k TopBeam) a pevná trubka z osy navíječe do nádrže vleku."""
    rx, ry, rz = REEL
    turns = 0.16 / (2 * HOSE_R)
    steps = int(turns * 32)
    x_in, x_out = rx + 0.08, rx - 0.08
    coil = []
    for k in range(steps + 1):
        s = k / steps
        a = math.pi / 2 + (1 - s) * turns * 2 * math.pi
        coil.append(Vector((x_in + (x_out - x_in) * s, ry + HOSE_COIL_R * math.sin(a), rz + HOSE_COIL_R * math.cos(a))))
    P.sweep("fillHoseCoil", coil, HOSE_R, "SDT_HoseBlack", segments=24)

    start = Vector(HOSE_START)
    feed = HOSE_FEED + [HOSE_START]
    P.sweep("HoseReel_0_Feed", P.hermite_path(feed, tangents={0: (0, 0, 1), len(feed) - 1: start - Vector(HOSE_FEED[-1])},
                                              samples=24), HOSE_R, "SDT_HoseBlack", segments=24)
    hx, hy = HOSE_HOLE
    P.ring_z("HoseGrommet", (hx, hy, TOP_SURF + 0.004), HOSE_R + 0.002, HOSE_R + 0.02, 0.008, "SDT_Rubber", segments=24)
    gz = POST_TOP + 0.03
    P.ring_z("HoseGuideRing", (hx, hy - 0.006, gz), HOSE_R + 0.004, HOSE_R + 0.012, 0.02, "SDT_Steel", segments=20)
    box("HoseGuideArm", -POST_X + POST / 2, hx - HOSE_R - 0.008, hy - 0.016, hy + 0.004, gz - 0.01, gz + 0.01, "SDT_Steel")
    cylinder_x("HoseReel_0_Swivel", (rx + 0.16, ry, rz), 0.03, 0.05, "SDT_Steel", segments=16)
    build_plumbing()


def build_plumbing():
    """Rozvod (sdt_tanks.build_plumbing): výpust hlavní nádrže vpředu dole a výpust indukční nádrže do T-kusu, z něj
    do sání čerpadla, výtlak čerpadla nahoře do otočné spojky navíječe."""
    rx, ry, rz = REEL
    T.build_plumbing(DECK_TOP, TANK_Y, TANK_R, TANK_LEN, (rx + 0.185, ry, rz), ceiling_z=TOP_SURF - TOP_PLATE)


def build_fill_hose():
    """Plnicí hadice z modrého navíječe (kontrakt kola 2).

    fillHoseStart = začátek volné hadice (Middle: v průchodce horní desky); fillHoseLay1..8 = body volně položené hadice
    (Middle: Lay1-2 hned za průchodkou, Lay3 konec pevného úseku, Lay8 = špička koncovky v klidu = fillHoseParkPos). fillHoseSeg1..96 = válce délky 1 m po +Z i3d s počátkem na začátku, v i3d rozložené po
    klidové křivce (natažené měřítkem z na délku tětivy + HOSE_R·tan(úhel ohybu / 2), aby v ohybu nebyla vidět
    mezera). Koncovka má počátek ve špičce a +Z i3d míří ze špičky ven.
    """
    vis = bpy.data.objects[ROOT_NAME]
    build_hose_reel_parts()
    hose = _group("fillHose", vis)
    start, lay, d = hose_lay_points()
    _group("fillHoseStart", hose, tuple(start))
    for i, p in enumerate(lay, 1):
        _group(f"fillHoseLay{i}", hose, tuple(p))
    pts = P.resample(hose_rest_path(), HOSE_SEGMENTS)
    for i in range(HOSE_SEGMENTS):
        a, b = pts[i], pts[i + 1]
        bend = (b - a).angle(pts[i + 2] - b) if i + 2 < len(pts) else 0.0
        length = (b - a).length + HOSE_R * math.tan(bend / 2)
        seg = tube(f"fillHoseSeg{i + 1}", (0, 0, 0), (0, -1, 0), HOSE_R, "SDT_HoseBlack", segments=24)
        seg.data.transform(seg.matrix_basis)
        seg.matrix_world = Matrix.Identity(4)
        _set_parent(seg, hose, Matrix.Translation(a) @ _aim(b - a) @ Matrix.Diagonal((1, length, 1, 1)))

    park = nozzle_park_matrix()
    _set_parent(P.group("fillHoseNozzle", N.nozzle_parts()), hose, park)
    _set_parent(_group("fillHoseParkPos", hose), hose, park)


def _physics(obj, **props):
    for k, v in props.items():
        obj["i3D_" + k] = v
    return obj


def _shape_box(name, parent, x0, x1, y0, y1, z0, z1, group_mask, **props):
    """Neviditelný kolizní/spouštěcí kvádr s počátkem v rodiči (vrcholy leží přímo na místě)."""
    return _as_shape(box(name, x0, x1, y0, y1, z0, z1, "SDT_Frame"), parent, group_mask, **props)


def _as_shape(obj, parent, group_mask, **props):
    world = obj.matrix_world.copy()
    obj.data.transform(world)
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_world = parent.matrix_world.copy() if parent else Matrix.Identity(4)
    obj.data.transform(obj.matrix_world.inverted())
    obj.display_type = "WIRE"
    obj.hide_render = True
    return _physics(obj, collisionFilterGroup=str(group_mask[0]), collisionFilterMask=str(group_mask[1]),
                    nonRenderable=True, **props)


_TO_I3D = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))


def i3d_rot_node(name, parent, loc, rot_i3d_deg):
    """Prázdný uzel, který po exportu (BAKE_TRANSFORMS: M_i3d = A @ M @ A^-1) dostane dané i3d natočení."""
    r = Euler([math.radians(a) for a in rot_i3d_deg], "XYZ").to_matrix().to_4x4()
    node = _group(name, parent, loc)
    node.matrix_world = Matrix.Translation(loc) @ (_TO_I3D.inverted() @ r @ _TO_I3D)
    return node


def _group(name, parent, loc=(0, 0, 0)):
    g = empty(name, loc)
    g.parent = parent
    g.matrix_parent_inverse = Matrix.Identity(4)
    g.matrix_world = Matrix.Translation(loc)
    return g


def equipment_collisions():
    """Kompaktní kolizní kvádry výbavy na spodní palubě (x0, x1, y0, y1, z0, z1). Hrdlo indukční nádrže zůstává volné
    (kvádr končí na horním okraji těla), skříň na kanystry je otevřená zepředu a žebřík i heliport jsou mimo."""
    z = DECK_TOP
    gx, gy = GEN_POS_MIDDLE
    px, py = T.PUMP_XY
    ix, iy = T.INDUCTION_XY
    tee = T.pump_ports(px, py, z)["tee"]
    rx, ry, rz = REEL
    rr = REEL_R + 0.06
    cx0, cx1, cy0, cy1, czw = chest_box()
    tb_x0, tb_x1, _, _ = T.TOOLBOX_XY
    cy0, cy1 = cabinet_y_range()
    return {
        **cabinet_collisions("Toolbox", tb_x0, tb_x1, cy0, cy1, z, ceiling=cabinet_ceiling()),
        "colGenerator": (gx - G.FX - 0.023, gx + G.FX + 0.023, gy - G.FY - 0.023, gy + G.FY + 0.023, z, z + 0.84),
        "colInductionTank": (ix - T.INDUCTION_R - 0.015, ix + T.INDUCTION_R + 0.015, iy - T.INDUCTION_R - 0.015,
                             iy + T.INDUCTION_R + 0.015, z,
                             z + T.INDUCTION_STAND_H + T.INDUCTION_CONE_H + T.INDUCTION_BODY_H),
        "colPump": (px - 0.262, px + 0.316, py - 0.185, py + 0.185, z, z + T.PUMP_AXIS_H + 0.25),
        "colMixer": (tee.x - 0.150, tee.x + 0.150, tee.y - 0.100, tee.y + 0.250, z, tee.z + 0.47),
        "colHoseReel": (rx - 0.12, rx + 0.12, ry - rr, ry + rr, rz - rr, POST_TOP),
        # truhla nabíječky nad horní palubou (Pavel 2026-10-07: chyběla, šlo se skrz) - jen zavřená výška, víko přes
        # ni o CHEST_OPEN_DEG neotáčíme, podobně jako ostatní sklápěcí díly nemají kolizi po celé dráze otevření
        "colChest": (cx0, cx1, cy0, cy1, TOP_SURF, czw + CHEST_LID_T),
        "colRelayCabinet": RELAY_CABINET[:4] + (DECK_TOP, RELAY_CABINET[5]),
    }


def build_i3d_structure(vis):
    """Uspořádání pro FS25 podle vanilla ABI Water Trailer 550: kolizní komponenta jako kořen."""
    rail_z0 = DECK_TOP - RAIL_H
    # vlastní tvar kořene je jen drobná krychle: skutečný box rámu je dětský tvar colChassis. Po zmrazení rozloženého vleku (kinematické těleso)
    # se kolize dětských tvarů vrací skriptem o těžiště zpět (SprayDroneStation.updateFreeze), kořenový tvar by zůstal posunutý
    comp = _shape_box(COMPONENT_NAME, None, -0.02, 0.02, 0.0, 0.04, DECK_TOP - 0.10, DECK_TOP - 0.06, COL_VEHICLE, dynamic=True,
                      compound=True)
    vis.parent = comp
    vis.matrix_parent_inverse = Matrix.Identity(4)

    cols = _group("collisions", comp)
    child = dict(compoundChild=True, density=0.001)
    _shape_box("colChassis", cols, -BASE_W / 2, BASE_W / 2, FRONT_Y + 0.01, BASE_Y1, rail_z0, DECK_TOP, COL_VEHICLE, **child)
    _shape_box("colTopDeck", cols, -TOP_W / 2, TOP_W / 2, TOP_Y0, TOP_Y1, POST_TOP, TOP_SURF, COL_VEHICLE, **child)
    for size in BT.TANK_SIZES:
        hw, ln, top = BT.tank_envelope(size)
        _shape_box(f"colTank{size}", cols, -hw, hw, BT.MAIN_TANK_Y_FRONT, BT.MAIN_TANK_Y_FRONT + ln, DECK_TOP,
                   DECK_TOP + top, COL_VEHICLE, **child)
    for name, box_ in equipment_collisions().items():
        _shape_box(name, cols, *box_, COL_VEHICLE, **child)
    _shape_box("colDrawbar", cols, -0.12, 0.12, COUPLER_Y + 0.20, BASE_Y0, COUPLER_Z - 0.05, COUPLER_Z + 0.08,
               COL_VEHICLE, **child)
    # sloupky horní desky a kryty kol (Pavel 2026-10-13: kolize všude); kryt jen jako deska nad kolem
    for side, sx in (("L", 1), ("R", -1)):
        for i, py in enumerate(POST_Y):
            px = sx * POST_X
            _shape_box(f"colPost{side}{i}", cols, px - POST / 2, px + POST / 2, py - POST / 2, py + POST / 2, DECK_TOP,
                       POST_TOP, COL_VEHICLE, **child)
        ca, cb = sorted((sx * (BASE_W / 2), sx * (TRACK_X + WHEEL_W / 2 + COVER_OVER)))
        _shape_box(f"colWheelCover{side}", cols, ca, cb, AXLE_Y[0] - COVER_R_OUT * 0.6, AXLE_Y[-1] + COVER_R_OUT * 0.6,
                   COVER_Z + COVER_R_OUT * 0.55, COVER_Z + COVER_R_OUT, COL_VEHICLE, **child)

    wheels = _group("wheels", vis)
    bpy.context.view_layer.update()
    for n, (ay, pos) in enumerate(zip(AXLE_Y, ("Front", "Back")), 1):
        for sx, side in ((1, "Left"), (-1, "Right")):
            wheel = _group(f"wheel{pos}{side}", wheels, (sx * TRACK_X, ay, WHEEL_R))
            # náboj a brzdový buben jedou s odpruženým kolem (hra ho posouvá po zdvihu), nezůstanou viset na rámu
            for part in (f"BrakeDrum_{n}{side[0]}", f"Hub_{n}{side[0]}"):
                if part in bpy.data.objects:
                    _set_parent(bpy.data.objects[part], wheel, bpy.data.objects[part].matrix_world.copy())

    fill = _group("fill", vis)
    # fillTrigger: postřikovač zajetý vedle vleku se z něj může dočerpat (fillTriggerVehicle)
    _shape_box("fillTrigger", fill, -BASE_W / 2 - 0.3, BASE_W / 2 + 0.3, FRONT_Y - 0.3, BASE_Y1 + 0.3, 0.0,
               DECK_TOP + 1.2, COL_TRIGGER, kinematic=True, compound=True, trigger=True)
    # exactFillRootNode: tady vlek "vidí" plnicí stanice a palety s hnojivem/herbicidem
    _shape_box("exactFillRootNode", fill, -TANK_R, TANK_R, TANK_Y - TANK_LEN / 2, TANK_Y + TANK_LEN / 2,
               DECK_TOP + 0.12, DECK_TOP + TANK_TOP, COL_FILL_ROOT, kinematic=True, compound=True)
    # concentrateFillRootNode: koncentrátová nádrž s plnicím hrdlem (nalévá se z kanystru, plní se z palet)
    _shape_box("concentrateFillRootNode", fill, *T.induction_fill_box(*T.INDUCTION_XY, DECK_TOP), COL_FILL_ROOT,
               kinematic=True, compound=True)
    # nádrž elektrocentrály: čerpací stanice a nádrž na naftu plní přes loadTrigger, který hledá exactFillRootNode
    _shape_box("dieselFillRootNode", fill, *G.fuel_fill_box(GEN_POS_MIDDLE, DECK_TOP), COL_FILL_ROOT, kinematic=True,
               compound=True)

    lights = _group("sharedLights", vis)
    for name, loc, rot in LIGHT_NODES:
        i3d_rot_node(name, lights, loc, rot)

    enter = _group("enterable", vis)
    _group("exitPoint", enter, EXIT_POINT)
    target = _group("outdoorCameraTarget", enter, CAMERA_TARGET)
    cam_data = bpy.data.cameras.get("outdoorCamera") or bpy.data.cameras.new("outdoorCamera")
    cam_data.lens = 22
    cam_data.clip_start = 0.3
    cam_data.clip_end = 5000
    cam = bpy.data.objects.new("outdoorCamera", cam_data)
    bpy.data.collections[COLLECTION_NAME].objects.link(cam)
    cam.parent = target
    cam.matrix_parent_inverse = Matrix.Identity(4)
    cam.matrix_world = Matrix.Translation(Vector(CAMERA_TARGET) + Vector((0, 8, 3)))

    occ = _group("tipOccluder", vis)
    _group("occlusionAreaStart", occ, (0.9, FRONT_Y, 0))
    _group("occlusionAreaWidth", occ, (-0.9, FRONT_Y, 0))
    _group("occlusionAreaHeight", occ, (0.9, BASE_Y1, 0))

    plate = _group("licensePlateBack", vis, (0, BASE_Y1 + 0.001, rail_z0 - 0.07))
    plate.rotation_euler = (0, 0, math.radians(180))
    return comp


def build_decals():
    """Nálepky vleku z atlasu (decal_layout.py): výstražné pruhy vpředu a vzadu na horní plošině a na zadním nosníku,
    polepky výbavy (sdt_labels); tenké čtyřúhelníky 1,5 mm nad povrchem. Na bocích horní plošiny malý lockup designu
    (beamL / beamR jako u Max, vidět i se srolovanou plachtou) místo dřívějšího nápisu SPRAY DRONE SERVICE."""
    ty = TOP_Y0 + 0.005
    z0, h = POST_TOP + 0.01, TOP_BEAM_H - 0.02
    w = 2 * (POST_X - POST / 2)
    P.decal_quad("Decal_StripeFront", (-w / 2, ty, z0), (1, 0, 0), (0, 0, 1), w, h, "stripe")
    P.decal_quad("Decal_StripeRear", (w / 2, -ty, z0), (-1, 0, 0), (0, 0, 1), w, h, "stripe")
    rz0, rh, rw = DECK_TOP - RAIL_H + 0.03, 0.12, 0.40
    sub = (0.0, 0.0, rw / rh / 16.0, 1.0)
    P.decal_quad("Decal_StripeRearL", (0.70, BASE_Y1, rz0), (-1, 0, 0), (0, 0, 1), rw, rh, "stripe", sub)
    P.decal_quad("Decal_StripeRearR", (-0.30, BASE_Y1, rz0), (-1, 0, 0), (0, 0, 1), rw, rh, "stripe", sub)
    bx = POST_X + POST / 2
    for side, sx in (("L", 1), ("R", -1)):
        P.brand_decal_set(f"beam{side}", "lockupOnDark", (sx * bx, TOP_Y0 + 0.40, POST_TOP + 0.067), (sx, 0, 0), (0, 0, 1),
                          0.40)
    SL.build_equipment_decals(DECK_TOP)


def build_drone_decals(prefix=DRONE_PREFIX):
    """Označení na obou bocích trupu dronu (pod barevným pásem), přitisknuté na zakřivený trup."""
    key, spec = drone_spec(prefix)
    bpy.context.view_layer.update()
    body = bpy.data.objects[prefix + "Body"]
    tilt = bpy.data.objects[prefix + "Tilt"]
    pts = [body.matrix_world @ Vector(c) for c in body.bound_box]
    c = sum(pts, Vector()) / 8
    half_x = (max(p.x for p in pts) - min(p.x for p in pts)) / 2
    width = 0.4 * spec["body"][0]
    zc = c.z - 0.2 * spec["body"][2]
    for side, sx in (("L", 1), ("R", -1)):
        d = P.conform_decal(f"{prefix}Decal_{side}", body, (c.x + sx * half_x, c.y, zc), (sx, 0, 0), (0, 0, 1),
                            width, width / 4, "drone" + key)
        _set_parent(d, tilt, d.matrix_world.copy())


VMASK_EXCLUDE_MATERIALS = ("SDT_NavLed",)
DRONE_MATERIAL_SUFFIX = "__D"


def dirt_atlas(obj):
    """Do které vmask patří mesh: 'drone' (trup, ramena, lůžko baterie, nálepky dronu), jinak 'trailer'."""
    if obj.name.startswith(tuple(DRONE_VARIANTS.values())) and "Clamp" not in obj.name:
        return "drone"
    return "trailer"


def dirt_meshes():
    colls = [bpy.data.collections[COLLECTION_NAME], bpy.data.collections[DRONE_COLLECTION]]
    out = []
    for coll in colls:
        for o in coll.objects:
            if o.type != "MESH" or o.get("i3D_nonRenderable"):
                continue
            if any(m and m.name.split(DRONE_MATERIAL_SUFFIX)[0] in VMASK_EXCLUDE_MATERIALS for m in o.data.materials):
                continue
            out.append(o)
    return out


def _ensure_uv0(obj):
    """První UV vrstva: krabicová projekce (u meshů bez UV), posunutá do kladných hodnot (mokrost ve vehicleShaderu
    chce UV0 s y > 0); nálepky mají UV0 v atlasu a nechají se."""
    me = obj.data
    if not me.uv_layers:
        bm = bmesh.new()
        bm.from_mesh(me)
        P._box_uv(bm)
        bm.to_mesh(me)
        bm.free()
    uv = me.uv_layers[0]
    uv.name = "UVMap"
    decal = {i for i, m in enumerate(me.materials) if m and m.name.split(DRONE_MATERIAL_SUFFIX)[0] in P.DECAL_MATERIALS}
    for poly in me.polygons:
        if poly.material_index in decal:
            continue
        for li in poly.loop_indices:
            u, v = uv.data[li].uv
            uv.data[li].uv = (u + 8.0, v + 8.0)


def _drone_materials(obj):
    me = obj.data
    for i, m in enumerate(me.materials):
        if m is None or m.name.endswith(DRONE_MATERIAL_SUFFIX):
            continue
        copy = bpy.data.materials.get(m.name + DRONE_MATERIAL_SUFFIX)
        if copy is None:
            copy = m.copy()
            copy.name = m.name + DRONE_MATERIAL_SUFFIX
        # konvertor exportéru slučuje materiály se stejnými hodnotami, kopie se proto musí nepatrně lišit
        c = list(m.diffuse_color)
        c[3] = 0.99
        copy.diffuse_color = c
        bsdf = next((n for n in copy.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if copy.node_tree else None
        if bsdf is not None:
            src = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            # kopie z dřívějšího sestavení zůstává v .blend: barvu převzít ze zdroje, ať platí změny ve slovníku MATERIALS
            for key in ("Base Color", "Metallic"):
                if not bsdf.inputs[key].is_linked:
                    bsdf.inputs[key].default_value = src.inputs[key].default_value
            bsdf.inputs["Roughness"].default_value = min(src.inputs["Roughness"].default_value + 0.01, 1.0)
        me.materials[i] = copy


def build_dirt_uvs():
    """Druhá UV vrstva 'DirtUV' pro vmask (špína v modrém, škrábance v červeném, AO v zeleném kanálu, vehicleShader
    varianta vmaskUV2): jedna společná rozvinutá plocha 0..1 pro celý vlek a jedna pro všechny tři drony
    (smart UV project všech meshů naráz). Meshe dronu dostanou vlastní kopie materiálů (__D), protože vmask je
    vlastnost materiálu."""
    meshes = dirt_meshes()
    groups = {"trailer": [], "drone": []}
    for o in meshes:
        _ensure_uv0(o)
        if dirt_atlas(o) == "drone":
            _drone_materials(o)
        me = o.data
        while len(me.uv_layers) > 1:
            me.uv_layers.remove(me.uv_layers[1])
        me.uv_layers.new(name="DirtUV")
        me.uv_layers.active_index = 1
        groups[dirt_atlas(o)].append(o)
    for name, objs in groups.items():
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in objs:
            o.hide_set(False)
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
        bpy.ops.object.mode_set(mode="OBJECT")
        print(f"DirtUV {name}: {len(objs)} meshů")
    for o in meshes:
        o.data.uv_layers.active_index = 0
        o.select_set(False)
    return groups


def move_to_preview(prefixes):
    """Modelovaná kola hra nepoužije (generuje je z rozměru pneu), v Blenderu zůstanou jako náhled."""
    prev = bpy.data.collections.get(PREVIEW_COLLECTION)
    if prev:
        for o in list(prev.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    else:
        prev = bpy.data.collections.new(PREVIEW_COLLECTION)
        bpy.context.scene.collection.children.link(prev)
    coll = bpy.data.collections[COLLECTION_NAME]
    for o in [o for o in coll.objects if o.name.startswith(prefixes)]:
        world = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = world
        coll.objects.unlink(o)
        prev.objects.link(o)


# teleskopy antén a GPS: (poloměr, výška horního konce nad palubou) pro každou sekci, odspodu. Při složení vleku se sekce 2 a 3
# zasunou do nižší o svou délku bez překryvu TELE_OVERLAP (animace foldLadder, uzly <jméno>Tele1 a <jméno>Tele2)
TELE_SECTIONS = {
    "antennaBoosted": [(0.016, 0.75), (0.012, 1.35), (0.008, 1.90)],
    "antennaLarge": [(0.018, 0.80), (0.014, 1.45), (0.010, 2.00)],
    "gpsRtkBox": [(0.012, 0.50), (0.009, 0.95), (0.007, 1.35)],
}
TELE_OVERLAP = 0.08


def tele_fold_parts():
    """Uzly teleskopů a jejich posun (i3d: osa Y nahoru) pro animaci skládání: [(uzel, startTrans, endTrans)]."""
    out = []
    for name, sections in TELE_SECTIONS.items():
        h = [z for _, z in sections]
        for k in (1, 2):
            local = h[k - 1] - (h[k - 2] if k == 2 else 0.0)
            retract = h[k] - h[k - 1] - TELE_OVERLAP
            out.append((f"{name}Tele{k}", local, local - retract))
    return out


def build_radio_gear(ant_xy=None, gps_xy=None):
    """Anténa vysílačky a GPS na palubě. Tři varianty antény podle obchodu, každá je vlastní uzel (objectChange):
    antennaBase = krátký sklolaminátový prut, antennaBoosted = teleskopický stožár s prutem, antennaLarge = teleskop se
    směrovou anténou (Yagi); gpsRtkBox = krabice přijímače a RTK anténa ve tvaru houby na teleskopické tyčce. Kořen každé
    varianty leží na patce, vysouvací sekce jsou vnořené uzly <jméno>Tele1 / Tele2 (při složení vleku se zasunou, viz
    tele_fold_parts). ant_xy / gps_xy dávají polohu ve světě (Max: u okraje kolem otočené truhly), jinak stojí vlevo od truhly."""
    vis = bpy.data.objects[ROOT_NAME]
    ox0, _, oy0, _, _ = chest_box()
    ax, base_y = ant_xy if ant_xy is not None else (ox0 - 0.22, oy0 + 0.10)
    zb = TOP_SURF

    def mount(prefix):
        return [box(f"{prefix}_Plate", ax - 0.05, ax + 0.05, base_y - 0.04, base_y + 0.04, zb, zb + 0.006, "SDT_Steel"),
                cylinder_z(f"{prefix}_Bolt1", (ax - 0.035, base_y - 0.025, zb + 0.006), 0.006, 0.006, "SDT_Frame", segments=6),
                cylinder_z(f"{prefix}_Bolt2", (ax + 0.035, base_y + 0.025, zb + 0.006), 0.006, 0.006, "SDT_Frame", segments=6),
                cylinder_z(f"{prefix}_Boot", (ax, base_y, zb + 0.031), 0.022, 0.05, "SDT_Rubber", segments=14)]

    def rig(name, x, y, levels):
        """Kořen na patce a vnořené uzly sekcí; levels = seznamy dílů pro kořen, Tele1, Tele2."""
        root = _group(name, vis, (x, y, zb))
        parent, z_prev = root, 0.0
        nodes = [root]
        for k in (1, 2):
            if len(levels) <= k:
                break
            z = TELE_SECTIONS[name][k - 1][1]
            node = _group(f"{name}Tele{k}", parent, (0, 0, 0))
            node.location = (0, 0, z - z_prev)
            bpy.context.view_layer.update()
            nodes.append(node)
            parent, z_prev = node, z
        bpy.context.view_layer.update()
        for node, parts in zip(nodes, levels):
            for o in parts:
                _set_parent(o, node, o.matrix_world.copy())
        return root

    def sections(prefix, secs, x, y, z_start):
        """Trubky a objímky po úrovních teleskopu."""
        levels, z0 = [], z_start
        for k, (r, z1) in enumerate(secs):
            lvl = [tube(f"{prefix}_Tube{k + 1}", (x, y, z0), (x, y, zb + z1), r, "SDT_PaintWhite", segments=12)]
            if k < len(secs) - 1:
                lvl.append(cylinder_z(f"{prefix}_Collar{k + 1}", (x, y, zb + z1), r + 0.005, 0.04, "SDT_Frame", segments=12))
            levels.append(lvl)
            # spodek další sekce začíná o překryv níž, aby v zasunutém stavu nebyla vidět mezera
            z0 = zb + z1 - TELE_OVERLAP
        return levels, zb + secs[-1][1]

    # základní: pevný prut
    base_parts = mount("antennaBase") + [
        tube("antennaBase_Tube1", (ax, base_y, zb + 0.056), (ax, base_y, zb + 0.75), 0.008, "SDT_PaintWhite", segments=12),
        cylinder_z("antennaBase_Cap", (ax, base_y, zb + 0.758), 0.010, 0.016, "SDT_Rubber", segments=10)]
    rig("antennaBase", ax, base_y, [base_parts])

    levels, top = sections("antennaBoosted", TELE_SECTIONS["antennaBoosted"], ax, base_y, zb + 0.056)
    levels[0] = mount("antennaBoosted") + levels[0]
    levels[2].append(cylinder_z("antennaBoosted_Cap", (ax, base_y, top + 0.008), 0.010, 0.016, "SDT_Rubber", segments=10))
    rig("antennaBoosted", ax, base_y, levels)

    levels, top = sections("antennaLarge", TELE_SECTIONS["antennaLarge"], ax, base_y, zb + 0.056)
    levels[0] = mount("antennaLarge") + levels[0]
    yz = top - 0.06
    levels[2] += [box("antennaLarge_Clamp", ax - 0.02, ax + 0.02, base_y - 0.03, base_y + 0.03, yz - 0.03, yz + 0.03, "SDT_Frame"),
                  tube("antennaLarge_Boom", (ax, base_y - 0.35, yz), (ax, base_y + 0.35, yz), 0.008, "SDT_Alu", segments=10),
                  box("antennaLarge_Feed", ax - 0.03, ax + 0.03, base_y - 0.24, base_y - 0.20, yz - 0.025, yz + 0.025,
                      "SDT_Rubber")]
    for k, (dy, half) in enumerate(((-0.32, 0.17), (-0.22, 0.15), (-0.08, 0.14), (0.06, 0.13), (0.20, 0.12), (0.33, 0.11))):
        levels[2].append(tube(f"antennaLarge_Element{k + 1}", (ax - half, base_y + dy, yz), (ax + half, base_y + dy, yz),
                              0.004, "SDT_Alu", segments=6))
    rig("antennaLarge", ax, base_y, levels)

    gx, gy = gps_xy if gps_xy is not None else (ax - 0.30, base_y)
    px = gx + 0.055
    levels, top = sections("gpsRtkBox", TELE_SECTIONS["gpsRtkBox"], px, gy, zb + 0.026)
    levels[0] += [
        box("gpsRtkBox_Plate", gx - 0.11, gx + 0.11, gy - 0.07, gy + 0.07, zb, zb + 0.006, "SDT_Steel"),
        P.chamfer_box("gpsRtkBox_Receiver", gx - 0.10, gx - 0.0, gy - 0.06, gy + 0.06, zb + 0.006, zb + 0.066,
                      "SDT_ChargerGrey", 0.006),
        box("gpsRtkBox_Band", gx - 0.101, gx - 0.0, gy - 0.061, gy + 0.061, zb + 0.040, zb + 0.052, "SDT_PaintYellow"),
        cylinder_z("gpsRtkBox_Led1", (gx - 0.075, gy - 0.061, zb + 0.022), 0.004, 0.004, "SDT_LedGreen", segments=8),
        cylinder_z("gpsRtkBox_Led2", (gx - 0.060, gy - 0.061, zb + 0.022), 0.004, 0.004, "SDT_LampAmber", segments=8),
        cylinder_z("gpsRtkBox_Led3", (gx - 0.045, gy - 0.061, zb + 0.022), 0.004, 0.004, "SDT_LampRed", segments=8),
        cylinder_z("gpsRtkBox_PoleFoot", (px, gy, zb + 0.016), 0.02, 0.02, "SDT_Rubber", segments=12),
        tube("gpsRtkBox_Cable", (gx, gy, zb + 0.03), (gx + 0.04, gy, zb + 0.03), 0.004, "SDT_HoseBlack", segments=6)]
    levels[2] += [cylinder_z("gpsRtkBox_Antenna", (px, gy, top + 0.015), 0.075, 0.03, "SDT_PaintWhite", segments=28,
                             radius_top=0.068),
                  cylinder_z("gpsRtkBox_Dome", (px, gy, top + 0.04), 0.06, 0.02, "SDT_PaintWhite", segments=28, radius_top=0.03)]
    rig("gpsRtkBox", px, gy, levels)


# ------------------------------------------------------------- Middle 2026-10-15: přední hrana nad ojí, plachta a polepy
TARP_X = 1.13                     # rovina boční plachty: vně sloupků (1,05) a složeného žebříku (1,105)
TARP_Z = (0.56, 2.335)            # spodní lem přes vnější líc podélníku (0,54-0,72) .. kolejnice pod TopBeam
TARP_FRONT_Z0 = 0.58
TARP_Y1 = BASE_Y1                 # zadní konec boku; záď je otevřená (skříň na kanystry s rolovacími vraty)
TARP_STRIPE_Z = (0.88, 1.00)
TARP_SIDE_STRAPS = (-2.45, -1.75, -1.00, -0.55, 0.40, 1.35, 2.18)   # y popruhů boku: mimo oblouky krytů kol
TARP_FRONT_STRAPS = (-0.75, 0.0, 0.75)
TARP_STRAP_TOP = TARP_STRIPE_Z[1] + 0.14     # krátké upínací popruhy jen dole, nad nimi je polep
TRACK_Z = (2.322, 2.344)          # kolejnice plachty pod TopBeam (nad ní nápis na boku TopBeam)
LOCKUP_MARK = 0.77                # průměr znaku (přes vrcholy) / výška oblasti lockupu v atlasu sdt_brand (BZUK)
SIDE_LOCKUP = (1.70, 0.84)        # boky: střed z, průměr znaku
FRONT_LOCKUP = (1.90, 2.00)       # předek: střed z, šířka lockupu
DOOR_MARK = 0.60                  # vrata skříně na kanystry: největší průměr znaku (lockup musí projít šířkou vrat)
DOOR_FIELD_Z0 = 1.08              # tmavé pole na vratech od této výšky po horní okraj
DOOR_STRIPE_Z = (0.90, 1.00)


def tarp_bottom(y):
    """Spodní hrana boční plachty v místě y: lem přes podélník, nad koly kopíruje oblouk krytu s 1 cm vůlí."""
    z = TARP_Z[0]
    for ay in AXLE_Y:
        d = abs(y - ay)
        if d < COVER_R_OUT:
            z = max(z, COVER_Z + math.sqrt(COVER_R_OUT ** 2 - d ** 2) + 0.010)
    return z


def build_front_extension():
    """Middle: nová přední hrana FRONT_Y nad ojí - prodloužené podélníky a paluba, dolní přední příčník pod předními sloupky;
    zásuvka 13pin s kabelem se přestěhuje pod nový příčník (Coupler_13PinDock a Coupler_13PinCable z build_coupler zmizí)."""
    rail_z0 = 0.58
    y0 = FRONT_Y + 0.01
    old = bpy.data.objects.get("FrontBeam")                 # dřívější čelo je teď uprostřed paluby: pod desku, ať nevyčnívá
    if old is not None:
        data = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        bpy.data.meshes.remove(data)
    box("FrontBeam", -BASE_W / 2 + RAIL_W, BASE_W / 2 - RAIL_W, BASE_Y0, BASE_Y0 + 0.08, DECK_TOP - RAIL_H,
        DECK_TOP - DECK_PLATE, "SDT_Frame")
    for side, sx in (("L", 1), ("R", -1)):
        x_out = sx * BASE_W / 2
        box(f"RailFront_{side}", x_out, x_out - sx * RAIL_W, y0, BASE_Y0, rail_z0, DECK_TOP, "SDT_Frame")
    box("FrontBeamOuter", -BASE_W / 2, BASE_W / 2, y0, y0 + POST, rail_z0, DECK_TOP, "SDT_Frame")
    box("DeckFront", -BASE_W / 2 + RAIL_W, BASE_W / 2 - RAIL_W, y0 + POST, BASE_Y0, DECK_TOP - DECK_PLATE, DECK_TOP - 0.005,
        "SDT_DeckWood")
    for name in ("Coupler_13PinCable", "Coupler_13PinDock"):
        o = bpy.data.objects.get(name)
        if o is not None:
            data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.meshes.remove(data)
    box("Coupler_13PinBracket", 0.39, 0.47, y0, y0 + 0.06, rail_z0 - 0.015, rail_z0, "SDT_Frame")
    box("Coupler_13PinDock", 0.40, 0.46, y0 - 0.006, y0, rail_z0 - 0.09, rail_z0 - 0.01, "SDT_Plastic")
    bz = COUPLER_Z
    wire = P.hermite_path([(0.43, y0 - 0.02, rail_z0 - 0.05), (0.36, -2.62, 0.575), (0.18, -2.86, 0.585), (0.11, -3.02, 0.575),
                           (0.09, -3.18, bz + 0.02), (0.08, -3.30, bz - 0.005)], samples=10)
    P.sweep("Coupler_13PinCable", wire, 0.006, "SDT_HoseBlack", segments=8)


def build_tarp_frame():
    """Pevné díly kolem plachty: kolejnice pod TopBeam (boky a předek), svislé rohové lišty vpředu a na zadním konci boku
    a konzoly pozičních světel sideMarker05 za koncem plachty."""
    za, zb = TRACK_Z
    mx, my, mz = SIDE_MARKER_POS
    xr = BASE_W / 2
    for side, sx in (("L", 1), ("R", -1)):
        box(f"TarpTrack_{side}", sx * TOP_W / 2, sx * (TARP_X + 0.02), FRONT_Y, TARP_Y1, za, zb, "SDT_Steel")
        # svislé lišty na konci plachty, dole patka k podélníku (vpředu za přední plachtou)
        for tag, y0, y1, z0, foot in (("F", FRONT_Y - 0.02, FRONT_Y + 0.02, TARP_FRONT_Z0 - 0.02, (FRONT_Y + 0.01, FRONT_Y + 0.03)),
                                      ("R", TARP_Y1 - 0.03, TARP_Y1 + 0.01, TARP_Z[0] - 0.02, (TARP_Y1 - 0.025, TARP_Y1 - 0.005))):
            box(f"TarpCorner_{side}{tag}", sx * (TARP_X - 0.02), sx * (TARP_X + 0.02), y0, y1, z0, za, "SDT_Frame")
            box(f"TarpCornerFoot_{side}{tag}", sx * xr, sx * (TARP_X - 0.02), *foot, 0.62, 0.66, "SDT_Frame")
        box(f"SideMarkerBracket_{side}", sx * (xr - 0.06), sx * (mx - 0.012), BASE_Y1 + 0.012, my + 0.015,
            mz - 0.03, mz + 0.03, "SDT_Frame")
        box(f"SideMarkerPlate_{side}", sx * (xr - 0.06), sx * xr, BASE_Y1, BASE_Y1 + 0.012, mz - 0.05, mz + 0.05, "SDT_Frame")
    box("TarpTrack_F", -(TARP_X + 0.02), TARP_X + 0.02, FRONT_Y - 0.04, FRONT_Y, za, zb, "SDT_Steel")


def build_tarps():
    """Rolovací plachty (sdt_parts.tarp): boky od přední hrany po zadní konec paluby s výřezem nad koly a předek; krátké
    popruhy jen dole. Postavené zavřené (stav složeného vleku), ve foldLadder se zavírají 2,6-3 s. Vrací {L, R, F: (pivot, role)}."""
    vis = bpy.data.objects[ROOT_NAME]
    z0, z1 = TARP_Z
    yc = (FRONT_Y + TARP_Y1) / 2
    straps = [y - yc for y in TARP_SIDE_STRAPS]
    out = {}
    for side, sx in (("L", 1), ("R", -1)):
        out[side] = P.tarp(f"tarpSide{side}", vis, (sx * TARP_X, yc, z1), (0, 1, 0), (sx, 0, 0), TARP_Y1 - FRONT_Y, z1 - z0,
                           drop_fn=lambda x: z1 - tarp_bottom(yc + x), straps=straps, strap_top=TARP_STRAP_TOP - z0)
    out["F"] = P.tarp("tarpFront", vis, (0, FRONT_Y, z1), (1, 0, 0), (0, -1, 0), 2 * TARP_X, z1 - TARP_FRONT_Z0,
                      straps=TARP_FRONT_STRAPS, strap_top=TARP_STRAP_TOP - TARP_FRONT_Z0)
    build_tarp_collisions(TARP_X, FRONT_Y, TARP_Y1, z1, tarp_bottom, FRONT_Y, TARP_FRONT_Z0)
    return out


TARP_COL_T = 0.04                 # tloušťka kolize plachty (dovnitř od roviny plachty)
# Bok plachty má jeden kvádr se spodkem v nejnižším bodě spodní hrany (nad koly zajede do krytu kola, týž kus vleku). Schody
# po obloucích (dřív krok 0,12 m = 9 kvádrů na bok) přetekly limit fyziky: kompound komponenty smí mít nejvýš 40 dětí VČETNĚ
# kol (log: "Failed to create compound ... with 43 children. Maximum is 40" - Middle pak neměl kolize vůbec, Max ztrácel
# kolizní tvary kol). Počítají se aktivní compoundChild (neaktivní nádrže z konfigurace ne), kořen a kola;
# hlídá tools/check_compound.py (v check_all). Max je s jedním kvádrem na bok na 39 / 40.
TARP_COL_STEP = 10.0              # nad koly nový kvádr, jakmile se spodní hrana plachty změní o víc (10 m = nikdy)


def _tarp_col_spans(y0, y1, bottom_fn, n=400):
    """Úseky (y od, y do, spodek) kolize boční plachty. Spodek úseku je nejnižší bod spodní hrany v něm: kvádr raději
    zajede do krytu kola (týž kus vleku), než aby u oblouku nechal mezeru."""
    spans = []
    for k in range(n):
        a, b = y0 + (y1 - y0) * k / n, y0 + (y1 - y0) * (k + 1) / n
        z = min(bottom_fn(a), bottom_fn((a + b) / 2), bottom_fn(b))
        if spans and abs(z - spans[-1][3]) <= TARP_COL_STEP:
            spans[-1][1], spans[-1][2] = b, min(spans[-1][2], z)
        else:
            spans.append([a, b, z, z])
    return [(a, b, z) for a, b, z, _ in spans]


def build_tarp_collisions(x, y0, y1, top, bottom_fn, front_y, front_bottom, fold_time=(2.6, 3.0)):
    """Kolize zavřených plachet (Middle i Max): tenké kvádry COL_VEHICLE na vnitřní straně roviny plachty, boky po úsecích
    podle spodní hrany, předek vcelku. Visí pod závěsy colTarpHinge{L,R,F} u horní hrany ve skupině "collisions". Při rolování
    (foldLadder, fold_time jako plachta) se závěs sklopí o 90° dovnitř a kvádry si lehnou do horní desky - kolize se jen
    otáčí, posun ani měřítko se neanimuje; posun o těžiště při zmrazení (SprayDroneStation.shiftCollisionShapes) dostane
    závěs jako ostatní děti skupiny."""
    cols = bpy.data.objects["collisions"]
    child = dict(compoundChild=True, density=0.001)
    t = TARP_COL_T
    hinges = []
    for side, sx in (("L", 1), ("R", -1)):
        hinge = _group(f"colTarpHinge{side}", cols, (sx * x, (y0 + y1) / 2, top))
        for k, (ya, yb, zb) in enumerate(_tarp_col_spans(y0, y1, bottom_fn)):
            _shape_box(f"colTarp{side}{k}", hinge, *sorted((sx * x, sx * (x - t))), ya, yb, zb, top, COL_VEHICLE, **child)
        hinges.append((hinge, "Y", sx * 90))
    hinge = _group("colTarpHingeF", cols, (0.0, front_y, top))
    _shape_box("colTarpF", hinge, -x, x, front_y, front_y + t, front_bottom, top, COL_VEHICLE, **child)
    hinges.append((hinge, "X", 90))
    t0, t1 = fold_time
    for hinge, axis, deg in hinges:
        rot = _TO_I3D @ Matrix.Rotation(math.radians(deg), 4, axis) @ _TO_I3D.inverted()
        hinge["sdt_mapped"] = 1
        hinge["sdt_fold_parts"] = (f'            <part node="{hinge.name}" startTime="{t0:g}" endTime="{t1:g}" '
                                   f'startRot="{P.i3d_fmt([math.degrees(v) for v in rot.to_euler("XYZ")])}" endRot="0 0 0"/>')
    print("kolize plachet: " + ", ".join(f"{h.name} {len(h.children)}" for h, _, _ in hinges))


def build_tarp_brand(tarps):
    """Polepy designů na plachtách (pod pivotem plachty, rolují se s ní): na bocích velký lockupOnDark (čte se zleva doprava
    při pohledu zvenku, vlevo je tak znak vpředu, vpravo vzadu) a pruh přes celou délku, vpředu menší lockup a pruh."""
    off = P.TARP_DECAL_OFFSET
    zl, mark = SIDE_LOCKUP
    h = mark / LOCKUP_MARK
    w = h * P.BL.aspect("lockupOnDark")
    zs, hs = sum(TARP_STRIPE_Z) / 2, TARP_STRIPE_Z[1] - TARP_STRIPE_Z[0]
    yc = (FRONT_Y + TARP_Y1) / 2
    for side, sx in (("L", 1), ("R", -1)):
        pivot, nrm, x = tarps[side][0], (sx, 0, 0), sx * (TARP_X + off)
        P.brand_decal_set(f"tarp{side}", "lockupOnDark", (x, yc, zl), nrm, (0, 0, 1), w, h, parent=pivot, offset=0.0,
                          tone=True)
        P.brand_decal_set(f"tarp{side}", "stripe", (x, yc, zs), nrm, (0, 0, 1), TARP_Y1 - FRONT_Y - 0.03, hs, parent=pivot,
                          offset=0.0, tag="Stripe")
    pivot, y = tarps["F"][0], FRONT_Y - off
    zf, wf = FRONT_LOCKUP
    P.brand_decal_set("tarpFront", "lockupOnDark", (0, y, zf), (0, -1, 0), (0, 0, 1), wf, parent=pivot, offset=0.0,
                      tone=True)
    P.brand_decal_set("tarpFront", "stripe", (0, y, zs), (0, -1, 0), (0, 0, 1), 2 * TARP_X - 0.03, hs, parent=pivot, offset=0.0,
                      tag="Stripe")
    print(f"polep boku: {w:.2f} x {h:.2f} m (znak {mark} m), předek {wf:.2f} m")


def _paint_material(name, color, roughness=0.6):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = (*color, 1.0)
    return mat


def build_rear_door_brand():
    """Rolovací vrata skříně na kanystry: místo nálepek Decal_Lid* (sdt_labels) pole v barvě plachty
    (SDT_Tarp, přebarvuje ho konfigurace barvy plachty) přes horní část, na něm lockup designu (bez podkladu; sada OnDark / OnLight podle barvy, brand_tone_group), pod ním pruh navazující na boky a malá výstražná ikona v rohu. Vše dítě pivotu vrat Toolbox_Door (při otevření se
    svine s plechem). Lockup je oříznutý na obsah designu a co největší, co projde šířkou vrat (znak nejvýš DOOR_MARK)."""
    for o in [o for o in bpy.data.objects if o.name.startswith("Decal_Lid")]:
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(data)
    pivot = bpy.data.objects["Toolbox_Door"]
    panel = bpy.data.objects["Toolbox_DoorPanel"]
    bpy.context.view_layer.update()
    pts = [panel.matrix_world @ Vector(c) for c in panel.bound_box]
    px0, px1 = min(p.x for p in pts), max(p.x for p in pts)
    pz1 = max(p.z for p in pts)
    face = max(p.y for p in pts) + 0.004                     # čelo lamel (plech je o lamelu za ním)
    cx = (px0 + px1) / 2
    fz0, fz1 = DOOR_FIELD_Z0, pz1 - 0.04
    field = box("RearDoor_Field", px0 + 0.03, px1 - 0.03, face + 0.0005, face + 0.0025, fz0, fz1, "SDT_Tarp")
    _set_parent(field, pivot, field.matrix_world.copy())
    avail = px1 - px0 - 0.16
    aspect = P.BL.aspect("lockupOnDark")
    for key in P.BL.DESIGN_ORDER:
        cw = min(1.0, P.BL.LOCKUP_CONTENT[key][0] + 0.02)
        full = min(DOOR_MARK / LOCKUP_MARK * aspect, avail / cw)
        P.brand_decal_set("rearDoor", "lockupOnDark", (cx, face + 0.0025, (fz0 + fz1) / 2), (0, 1, 0), (0, 0, 1), full * cw,
                          full / aspect, parent=pivot, designs=(key,), sub=(0.5 - cw / 2, 0.0, 0.5 + cw / 2, 1.0),
                          tone=True)
    P.brand_decal_set("rearDoor", "stripe", (cx, face, sum(DOOR_STRIPE_Z) / 2), (0, 1, 0), (0, 0, 1), px1 - px0 - 0.06,
                      DOOR_STRIPE_Z[1] - DOOR_STRIPE_Z[0], parent=pivot, tag="Stripe")
    s = 0.13
    warn = P.decal_quad("RearDoor_Warn", (px0 + 0.05 + s, face, DOOR_STRIPE_Z[0] - 0.03 - s), (-1, 0, 0), (0, 0, 1), s, s,
                        "boxWarn")
    _set_parent(warn, pivot, warn.matrix_world.copy())


def build():
    coll, vis = P.begin(COLLECTION_NAME, ROOT_NAME)
    build_chassis()
    build_wheel_arches()
    build_drawbar()
    build_front_extension()
    build_upper_structure()
    build_slide_ladder()
    build_equipment()
    build_i3d_structure(vis)
    move_to_preview(("Wheel_", "Rim_"))
    build_drones()
    for prefix in DRONE_VARIANTS.values():
        place_drone(prefix)
        build_drone_leds(prefix)
        build_drone_clamps(prefix)
    build_heliport()
    build_batteries()
    build_charger()
    attach_batteries()
    build_charger_chest()
    build_radio_gear()
    build_charger_cable()
    for prefix in DRONE_VARIANTS.values():
        build_drone_service_parts(prefix)
        build_drone_decals(prefix)
    build_fill_hose()
    build_decals()
    build_rear_door_brand()
    build_relay_holders()
    build_planner_tablet()
    build_tarp_frame()
    build_tarp_brand(build_tarps())
    bpy.context.view_layer.update()
    build_dirt_uvs()
    print(f"{COLLECTION_NAME}: {len(coll.objects)} objektů")


if __name__ == "__main__":
    build()
