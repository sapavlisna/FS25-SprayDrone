"""Malý servisní vlek: všechno na jedné palubě, bez horní desky. Dron S stojí složený na palubě uvnitř bedny z tří skládacích panelů
na zadním konci paluby; při rozložení se panely sklopí do plošiny za vlekem (na nožičkách), dron se na ni otočí a přejede
(scripts/SprayDronePad.lua).

Skládá se z velkého skriptu build_trailer_middle.py: ten se spustí do stejného jmenného prostoru, přepíšou se rozměry a
funkce nástavby, podvozek, oj, dron (S), úchyty lyžin, rozkládání dronu a mapy špíny zůstanou stejné. Uspořádání shora
(+X vlevo, -Y dopředu k oji):

    vpředu         elektrocentrála vlevo (otočená: panel vpřed, hrdlo nádrže vlevo vpředu), vpravo indukční nádrž;
                   za nimi čerpadlo a mixér, šachta baterií (otočená napříč) za centrálou
    uprostřed      nízká hranatá nádrž 0,90 x 0,98 x 0,369 m (300 l), po bocích u lemů paluby dvě bedny na 4 kanystry (víka se
                   otevírají dovnitř, popisek nádrže leží na horní ploše); výtlak čerpadla vede nad nádrží
    za nádrží      navíječ plnicí hadice vpravo u lemu (modrý buben s osou podél vleku), hadice z něj vychází stranou ke středu a plynulou
                   smyčkou dozadu, po rozložení bedny leží na odkryté palubě pod bednou
    vzadu          bedna s dronem přes celou šířku vleku (zelené panely P - H - Z na čepech, plechové boční stěny, nožičky v rozích
                   panelů; při rozložení se boční stěny nejdřív vyklopí ven a sklopí k zemi vedle vleku). Polepy značky podle konfigurace
                   Design (BZUK / ROSA / kapka / STRATUS AGRI, uzly brand_<KEY>_<místo>): na všech vnějších stranách bedny, na vnitřní
                   (pochozí) straně bočních stěn, na plošině za heliportem a znak na bocích beden na kanystry

Spuštění v Blenderu:
    p = r"...\build_trailer_mini.py"; exec(open(p, encoding="utf-8").read(), {"__file__": p, "__name__": "__main__"})
Bez okna (přestavba + uložení do spraydrone_trailer_mini.blend): viz headless_mini.py.
"""

import math
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_big = os.path.join(_HERE, "build_trailer_middle.py")
exec(compile(open(_big, encoding="utf-8").read(), _big, "exec"), globals())


def _rename_new(before, suffix):
    """Přejmenuje objekty vzniklé od snímku before (množina jmen) tak, aby měly příponu suffix místo Blenderova .001."""
    for o in [o for o in bpy.data.objects if o.name not in before]:
        base = o.name.rsplit(".", 1)[0] if o.name[-4:-3] == "." and o.name[-3:].isdigit() else o.name
        o.name = base + suffix


def _transform_new(before, matrix):
    """Posune a otočí nově vzniklé objekty (jen kořenové, jejich děti jedou s nimi)."""
    for o in [o for o in bpy.data.objects if o.name not in before]:
        if o.parent is None or o.parent.name in before:
            o.matrix_world = matrix @ o.matrix_world
    bpy.context.view_layer.update()

# ---------------------------------------------------------------------------------------------------------- konstanty
V = T.V
L = BT.L

COLLECTION_NAME = "SprayDroneTrailerMini"
PREVIEW_COLLECTION = "SprayDroneTrailerMini_Preview"
COMPONENT_NAME = "sprayDroneTrailerMini_main_component1"
ROOT_NAME = "sprayDroneTrailerMini_vis"

BASE_LEN = 4.00                      # za nádrží a bednami na kanystry leží navíječ hadice a za ním složená bedna s dronem (1,35 m hluboká,
                                     # kotvená na zadním konci paluby)
BASE_W = 1.86
BASE_Y0 = -2.60
COUPLER_Y = -4.45                    # oj 1,85 m: čelo vleku se u velkých tahačů dotkne pneumatiky až nad 50° zalomení
JOCKEY_Y = COUPLER_Y + 0.875         # rameno oje je tu v x ~0,17 jako u Middle, takže zvednuté kolečko (x 0,265-0,335) oj míjí
_Y = BASE_Y0 + 2.10                 # posun polohy po ose Y oproti návrhu s palubou od -2,10
BASE_Y1 = BASE_Y0 + BASE_LEN
TRACK_X = 1.11                       # kola vně rámu jako u Utili Trailer 2 (vnitřní líc pneu 0,95 těsně za lemem paluby 0,93), nad nimi blatníky
AXLE_Y = [-0.45]                     # jedna náprava pod zadní částí nádrže a beden: s bednou na zadním konci vychází zátěž oje ~12 % (viz HITCH_LOAD)
# pneu jako u Middle (vanilla 320/60 R12, kategorie TRAILER, výška 0,71 m): 425/55 R17 (Ø 0,9 m) byla traktorová kola a procházela palubou;
# kola jsou teď vně rámu, takže už palubou procházet nemohou
TIRE_DIMENSIONS = "320_60R12"
WHEEL_R = 0.354
WHEEL_W = 0.32
TIRE_FILE = "$data/shared/wheels/tires/lizard/destinationFarm/280_70R15.xml"      # jako Middle, viz tam
TIRE_Y_OFFSET = 0.031
RIM_KIND, RIM_FILE, RIM_WIDTH_DIAM = "R15", "wheels/sdtRim15.i3d", "8 15.5"
LEGACY_WHEEL_IDS = ("DEFAULT_TRELLEBORG_T421", "TRELLEBORG_T421_320_55R15", "TRELLEBORG_T421_280_60R15_5",
                    "TRELLEBORG_AW305_10_80R12", "BKT_I1_11L_14", "BKT_PL801_250_70R15")
TIRE_REST_LOAD, TIRE_COMPRESSION, TIRE_SUSP_TRAVEL = 0.8, 15, 0.05
TIRE_SPRING, TIRE_DAMPER, TIRE_FRICTION = 55, 25, 1.6

DRONE_VARIANTS = {"S": "Drone_S_"}
DRONE_PREFIX = DRONE_VARIANTS["S"]
DRONE_HIDDEN = ()
BATTERY_COUNT = 4

PAD_W, PAD_H, PAD_L = 0.90, 0.3691, 0.98    # nízká hranatá nádrž 300 l: vnitřní objem zaoblené krabice (stěna PAD_WALL) vychází na 300,0 l
                                            # (pad_tank_liters), šířka vyplňuje prostor mezi bednami na kanystry (víka beden se otevírají
                                            # těsně k nádrži), délka sahá až k navíječi hadice
PAD_WALL = 0.007
PAD_GAP = 0.04
PAD_Y0 = -0.84 + _Y                         # přední stěna; výpust v kontraktu je o 3 cm za ní; 7 cm před ní končí šachta baterií (kabel nabíječky vede v mezeře)
PAD_LITERS = 300
TANK_TOP = DECK_TOP + PAD_GAP + PAD_H

# Bedna nad dronem (nahrazuje dřívější dvoudílnou vysouvací desku, Pavel 2026-10-08/09): tři ploché panely P (přední stěna) -
# H (horní víko) - Z (zadní stěna) svisle/vodorovně/svisle tvoří ve složeném stavu bednu, která celou základnou stojí na palubě
# přes dron (žádná mezideska pod ním - dron sedí přímo na palubě). Při rozložení se panely sklopí do jedné roviny (čep na konci
# jednoho = čep dalšího, řetězem) a vytvoří samostatnou plošinu na vlastních nožičkách; teprve potom se dron nadzvedne, otočí a přejede
# doprostřed ní. Dron je ve složené bedně otočený o 90° navíc (DRONE_EXTRA_ROT), aby se vešel na šířku vleku místo na její délku -
# při rozložení se otočí zpátky do letové orientace (nos po směru jízdy, hrdlo nádrže dronu na straně navíječe hadice).
CRATE_HX = BASE_W / 2                       # půlšířka bedny = půlšířka vleku (od okraje k okraji včetně bočních lemů)
CRATE_H = 0.845                             # výška bedny = délka panelu P i Z po rozložení
CRATE_LH = 1.346                            # hloubka bedny (= délka panelu H), podle otočeného dronu + rezerva
CRATE_WALL_T = 0.02
CRATE_Y_ANCHOR = BASE_Y1                    # kotva (čep k palubě) na konci vleku, bedna sahá dopředu od ní
CRATE_Z0 = DECK_TOP                         # dron stojí přímo na palubě
TOP_SURF = CRATE_Z0                         # place_drone() cíl - dřív horní plocha desky, teď paluba
DRONE_Y = CRATE_Y_ANCHOR - CRATE_LH / 2     # střed dronu ve složené bedně
DRONE_EXTRA_ROT = math.pi / 2               # dron navíc otočený o 90° ve složené bedně (viz výš)
CAMERA_TARGET = (0.0, DRONE_Y, CRATE_Z0 + CRATE_H / 2)
HITCH_LOAD = 0.14                           # podíl váhy na oji (cíl 10-20 %): (z_těžiště - z_nápravy) / (z_spojky - z_nápravy)
CENTER_OF_MASS = (0.0, AXLE_Y[0] + (COUPLER_Y - AXLE_Y[0]) * HITCH_LOAD, 0.75)
EXIT_POINT = (BASE_W / 2 + 1.0, BASE_Y1 - 0.6, 0.0)

GEN_POS = (0.50, -2.15)                     # centrála vpředu vlevo, otočená o -90°: panel vpřed, hrdlo nádrže vlevo vpředu
GEN_ROT = -math.pi / 2
GEN_SOCKET_LOCAL = (GEN_POS[0] + 0.33, GEN_POS[1] - 0.10, 1.15)     # zásuvka v neotočeném stavu (tak ji staví sdt_generator)
GEN_SOCKET = (GEN_POS[0] - 0.10, GEN_POS[1] - 0.33, 1.15)           # po otočení: na čelním panelu
CLUSTER_SHIFT = (-0.03, -0.57 + _Y)            # čerpadlo, indukční nádrž a výpust jako u velkého vleku, posunuté sem
PUMP_XY = (-0.55 + CLUSTER_SHIFT[0], -0.55 + CLUSTER_SHIFT[1])
INDUCTION_XY = (-0.55 + CLUSTER_SHIFT[0], -1.25 + CLUSTER_SHIFT[1])
MAIN_DRAIN = Vector((0.095 + CLUSTER_SHIFT[0], -0.239 + CLUSTER_SHIFT[1], 1.0025))

STRIP_X = (0.40, 0.72)                      # původní pás šachty baterií (její geometrie se staví tady a pak se přesune za centrálu)
BAY_Y = (-0.80 + _Y, -0.04 + _Y)
BAY_CELLS = tuple(c + _Y for c in (-0.705, -0.515, -0.325, -0.135))   # čtyři šachty baterií (do 2026-10-15 tři a ovládací panel)
BAY_SHAFT = (0.21, 0.13)
BAY_WALL = 0.03
BAY_FEET = 0.015
BAY_DOCK = 0.035
BAY_LID_CLEAR = 0.085
BAY_LID_T = 0.025
BAY_LID_OPEN_DEG = 100
BAY_LID_BASIS = Euler((0, 0, -math.pi / 2)).to_matrix().to_4x4()     # závěs u nádrže: osa závěsu = Y vleku, víko míří ven
BAY_ROTATE_MATRIX = Matrix.Rotation(math.radians(90), 4, "Z")     # otočení šachty při přesunu za centrálu; export z ní dopočítá
                                            # zavřenou pozici víka (BAY_LID_BASIS je definovaná před přesunem). Musí to být konstanta modulu:
                                            # export modul jen načte a build() nespouští, takže dřív dostal jednotkovou matici a zavřené víko
                                            # se animovalo do Rz(-90°) místo do klidové polohy
LID_TIME = (11.0, 12.0)                    # s v animaci foldTrailer (12 s): víko se otevírá jako první a zavírá jako poslední
CABLE_TIME = (0.0, 0.05)
BOX_X = (-0.865, -0.545)                   # bedna u pravého lemu (x záporné); druhá je zrcadlově u levého, nádrž je mezi nimi
BOX_Y = (-0.83 + _Y, -0.03 + _Y)
BOX_H = 0.46
BOX_SLOTS = 4
BOX_PITCH = 0.20
# druhá bedna (duplikát, Pavel 2026-10-07): na místě bývalé šachty baterií, zrcadlově přes nádrž - stejná šířka jako
# STRIP_X u baterií, stejný Y rozsah jako první bedna
BOX2_X = (0.545, 0.865)
# šachta baterií se přesouvá do mezery mezi zadní stěnou centrály (y -1,767) a přední stěnou nádrže (y -1,37);
# přirozená orientace šachty je úzká-dlouhá (podél Y), mezera je široká-mělká - staví se na místě a pak se otočí o 90°
BAY2_GAP_X = (0.10, 0.90)
BAY2_GAP_Y = (-1.74, -1.40)

LIGHT_NODES = [
    ("rearLight52_left", (0.78, BASE_Y1 + 0.005, DECK_TOP - RAIL_H + 0.08), (-90, 0, 180)),
    ("rearLight52_right", (-0.78, BASE_Y1 + 0.005, DECK_TOP - RAIL_H + 0.08), (-90, 0, 180)),
    ("plateNumberLight03", (0.0, BASE_Y1 + 0.005, DECK_TOP - RAIL_H - 0.005), (-90, 0, -90)),
    ("sideMarker05_left", (BASE_W / 2 + 0.003, BASE_Y1 - 0.12, DECK_TOP - RAIL_H + 0.09), (0, 0, -90)),
    ("sideMarker05_right", (-BASE_W / 2 - 0.003, BASE_Y1 - 0.12, DECK_TOP - RAIL_H + 0.09), (0, 0, 90)),
]

# plnicí hadice: navinutá na modrém navíječi (osa podél vleku, bočnice, konzoly na obou koncích osy, otočný přívod na předním konci u
# nádrže; fillHoseCoil) na palubě vpravo za nádrží; hadice vychází z poslední otáčky vespod stranou ke středu a plynulou smyčkou
# zatáčí dozadu přes vodítko, po rozložení bedny leží po odkryté zadní části paluby (pod bednou) k držáku koncovky; Lay1-3 jsou
# pevný úsek (Lay3 je jeho konec), Lay4-8 volná část. Volná část musí dosáhnout k dronu uprostřed
# plošiny za koncem paluby (SprayDronePad.hoseReaches: potřebná délka ~ 1,12 x vzdálenost + 0,2 m).
REEL_X, REEL_Y = -0.72, -0.20
REEL_R_CORE, REEL_R_FLANGE = 0.13, 0.175
REEL_Z = DECK_TOP + 0.015 + REEL_R_FLANGE
COIL_R = REEL_R_CORE + HOSE_R
COIL_HALF = 0.035                           # polovina šířky vinutí podél osy
SWIVEL_Y = REEL_Y - 0.1075                  # otočný přívod na předním konci osy (u nádrže)
DECK_HOSE_Z = DECK_TOP + HOSE_R + 0.006
CRATE_FRONT_Y = CRATE_Y_ANCHOR - CRATE_LH   # přední stěna bedny (u nádrže)
HOSE_START = (REEL_X, REEL_Y + COIL_HALF, REEL_Z - COIL_R)
_Y1 = BASE_Y1
HOSE_LAY = [(-0.419, -0.143, DECK_HOSE_Z), (-0.210, 0.119, DECK_HOSE_Z), (-0.304, 1.097, DECK_HOSE_Z),
            (0.062, _Y1 - 0.065, DECK_HOSE_Z), (0.35, _Y1 - 0.07, DECK_HOSE_Z), (0.72, _Y1 - 0.18, DECK_HOSE_Z),
            (0.86, _Y1 - 0.54, DECK_HOSE_Z), (0.60, _Y1 - 0.90, DECK_HOSE_Z)]
HOSE_GUIDE_X = REEL_X + 0.20                # vodítko hadice (brána) stojí hned za bočnicí navíječe, kde hadice míří ke středu vleku
HOSE_PARK_TIP = (-0.14, _Y1 - 1.08, DECK_HOSE_Z + 0.006)      # špička koncovky (kov) stojí kousek před sousedním úsekem hadice, neprochází jím
HOSE_PARK_DIR = (-0.99, 0.0, 0.0)
FOLD_DURATION = 12.0                        # s: délka animace foldTrailer (víko šachty končí ve 12 s)
DRONE_UNFOLD_TIME = 2.6                     # s: do tohoto času animace se rozkládá dron, před ním je bedna hotová
CLAMP_TIME = (10.6, 11.0)                   # s v animaci foldTrailer: bedna s dronem je zajištěná (securedFoldTime), víko ještě otevřené

# sdílené moduly nádrží čtou polohu čerpadla, indukční nádrže a výpusti z modulových konstant
T.PUMP_XY, T.INDUCTION_XY, T.MAIN_DRAIN = PUMP_XY, INDUCTION_XY, MAIN_DRAIN
BT.MAIN_DRAIN = MAIN_DRAIN


# ---------------------------------------------------------------------------------------------------- hranatá nádrž
class PadTank(BT.BoxTank):
    """Hranatá nádrž pod dronem se stejným rozhraním jako BoxTank (výpust, armatury)."""

    def __init__(self, z):
        self.size = PAD_LITERS
        self.W, self.H, self.Ln = PAD_W, PAD_H, PAD_L
        self.hw = PAD_W / 2
        self.z = z
        self.y0 = PAD_Y0
        self.zb = z + PAD_GAP
        self.zt = self.zb + PAD_H
        self.zc = self.zb + PAD_H / 2
        self.top_z = self.zt
        self.mid = PAD_L / 2
        self.rn = 0.12
        self.wv = 0.26


def pad_tank_liters(width=None, length=None, height=None):
    """Vnitřní objem nádrže v litrech: stejná zaoblená krabice jako vnější plášť, zmenšená o tloušťku stěny PAD_WALL."""
    w, ln, h = width or PAD_W, length or PAD_L, height or PAD_H
    t = bmesh.new()
    bmesh.ops.create_cube(t, size=1.0, matrix=Matrix.Diagonal((w - 2 * PAD_WALL, ln - 2 * PAD_WALL, h - 2 * PAD_WALL, 1.0)))
    bmesh.ops.bevel(t, geom=list(t.edges), offset=BT.BOX_EDGE_R - PAD_WALL, offset_type="OFFSET", segments=3, profile=0.5,
                    affect="EDGES")
    liters = t.calc_volume() * 1000.0
    t.free()
    return liters


def pad_label_geometry(t):
    """Jednotný popisek na horní ploše nádrže (boky zakrývají bedny na kanystry): objem a výstražný štítek vedle sebe za hrdlem, čitelné
    zezadu (zprava doleva roste x). {jméno: (x střed, u od přední stěny, šířka, výška)}"""
    wv = 0.26
    hv = wv / 1.6
    wp = 0.12
    hp = wp / 1.6
    u = 0.66
    return {"vol": (-0.07, u, wv, hv), "plate": (0.15, u, wp, hp)}


def build_pad_tank():
    """Nízká hranatá PE nádrž 300 l (0,90 x 0,98 x 0,369 m, vnitřní objem 300 l, viz pad_tank_liters): zaoblený kvádr, plnicí hrdlo
    s víkem nahoře, odvzdušnění, výpust vpředu jako u velkého vleku, vypouštěcí kohout vzadu a jeden popisek na horní ploše."""
    z = DECK_TOP
    t = PadTank(z)
    name = "Tank_Main"
    shell, fit, lid, frm = (BT.Mesh(n) for n in (name, f"{name}_Fittings", f"{name}_Lid", f"{name}_Frame"))
    hw = t.hw
    BT._rounded_box(shell, -hw, hw, t.y0, t.y0 + t.Ln, t.zb, t.zt, BT.PE, BT.BOX_EDGE_R)
    lab = pad_label_geometry(t)
    for key in ("vol", "plate"):
        x, u, w, h = lab[key]
        y = t.y0 + u
        bar, rise = (0.010, 0.005) if key == "vol" else (0.007, 0.003)
        x0, x1, y0, y1 = x - (w + 0.03) / 2, x + (w + 0.03) / 2, y - (h + 0.03) / 2, y + (h + 0.03) / 2
        zt = t.zt
        shell.box(x0, x1, y0, y0 + bar, zt - 0.002, zt + rise, BT.PE)
        shell.box(x0, x1, y1 - bar, y1, zt - 0.002, zt + rise, BT.PE)
        shell.box(x0, x0 + bar, y0, y1, zt - 0.002, zt + rise, BT.PE)
        shell.box(x1 - bar, x1, y0, y1, zt - 0.002, zt + rise, BT.PE)
        if key == "plate":
            shell.box(x - (w + 0.012) / 2, x + (w + 0.012) / 2, y - (h + 0.012) / 2, y + (h + 0.012) / 2, zt - 0.002, zt + 0.001,
                      BT.PE)

    BT._manway(t, shell, fit, lid, 0.22)
    BT._vent_at(fit, V(0.30, t.y0 + 0.22, t.zt), V(0, 0, 1), 0.8)
    BT._outlet(t, fit)
    BT._rear_drain_at(fit, V(0.24, t.y0 + t.Ln, t.zb + 0.12), V(0, 1, 0), V(0, 0, -1), 0.45)
    BT._box_frame(t, frm, eyes=False)
    meshes = [m.finish() for m in (shell, fit, lid, frm)]
    bpy.context.view_layer.update()

    decals = []
    for key, region, offset in (("vol", f"tankVol{PAD_LITERS}", 0.0022), ("plate", f"tankPlate{PAD_LITERS}", 0.0025)):
        x, u, w, h = lab[key]
        uax, vax = V(-1, 0, 0), V(0, -1, 0)
        c = V(x, t.y0 + u, t.zt)
        decals.append(P.decal_quad(f"{name}_{key.capitalize()}", c - uax * w / 2 - vax * h / 2, uax, vax, w, h, region, offset=offset))
    P.group("tankMain", meshes + decals)
    return t


# --------------------------------------------------------------------------------------------- čerpadlo, mixér, rozvod
def build_mini_plumbing(z):
    """Rozvod jako T.build_plumbing bez výtlačné hadice k navíječi: sání čerpadla, mixér, hadice z výpusti nádrže a
    z indukční nádrže; výtlak čerpadla končí zaslepenou rychlospojkou."""
    import sdt_mixer as X
    importlib.reload(X)
    px, py = PUMP_XY
    ix, iy = INDUCTION_XY
    pp = T.pump_ports(px, py, z)
    fit = T.Mesh("Plumbing")
    hz = pp["axis_z"]
    inl, el, tee = pp["inlet"], pp["elbow"], pp["tee"]
    fit.flange(inl + V(0.001, 0, 0), V(1, 0, 0), 0.070, 0.016, "SDT_Steel", bolts=4, bolt_r=0.054, bolt_size=0.007,
               phase=math.radians(45))
    fit.cyl(inl + V(0.017, 0, 0), el, 0.031, "SDT_Steel", seg=18)
    fit.cyl(inl + V(0.040, 0, 0), inl + V(0.070, 0, 0), 0.041, "SDT_Steel", seg=6)
    fit.sphere(el, 0.040, "SDT_Steel", seg=18, rings=9)
    fit.cyl(el + V(0, T.TEE_DY * 0.45, 0), el + V(0, T.TEE_DY * 0.45 - 0.030, 0), 0.041, "SDT_Steel", seg=6)
    X.build_mixer(tee, z, el)
    ports = X.mixer_ports(tee)

    o = pp["outlet"]
    fit.flange(o + V(0, 0, 0.001), V(0, 0, 1), 0.058, 0.014, "SDT_Steel", bolts=4, bolt_r=0.045, bolt_size=0.0065,
               phase=math.radians(45))
    fit.cyl(o + V(0, 0, 0.016), o + V(0, 0, 0.034), 0.030, "SDT_Steel", seg=16)
    fit.ball_valve(o + V(0, 0, 0.034), o + V(0, 0, 0.120), 0.030, V(-1, 0, 0), "SDT_ValveBlue", lever_len=0.14)
    fit.cyl(o + V(0, 0, 0.120), o + V(0, 0, 0.134), 0.033, "SDT_Brass", seg=6)
    fit.hose_tail(o + V(0, 0, 0.134), o + V(0, 0, 0.186), 0.0255)
    fit.clamp(o + V(0, 0, 0.172), V(0, 0, 1), 0.0255)
    top = o + V(0, 0, 0.170)
    # výtlak: z výpusti čerpadla krátce nahoru a přes čelo bedny dozadu k mezeře mezi nádrží a pravou bednou, tou nízko při palubě dozadu
    # a za zadní stěnou bedny po palubě k navíječi, kde stoupá k otočnému přívodu na předním konci jeho osy (vstupuje do něj v ose podél vleku)
    gx = (-PAD_W / 2 + BOX_X[1]) / 2                  # střed mezery mezi nádrží (x -0,45) a bednou (x -0,545)
    yb = (PAD_Y0 + PUMP_XY[1] + 0.185) / 2            # mezi zadním čelem čerpadla a přední stěnou nádrže
    zd = DECK_TOP + T.HOSE_R + 0.012
    zo = top.z + 0.07
    yt = SWIVEL_Y - 0.0175 - 0.03
    y_jog = BOX_Y[1] + 0.07                           # zalomení k navíječi hned za zadní stěnou bedny
    corners = [top, V(top.x, top.y, zo), V(gx, yb, zo), V(gx, yb, zd), V(gx, y_jog, zd), V(REEL_X, y_jog, zd),
               V(REEL_X, y_jog, REEL_Z), V(REEL_X, yt, REEL_Z)]
    pipe = T.rounded_path(corners, [0.06, 0.06, 0.07, 0.05, 0.05, 0.05])
    P.sweep("Pump_Discharge", pipe, T.HOSE_R, "SDT_HoseBlack", segments=24)
    fit.cyl(V(REEL_X, yt, REEL_Z), V(REEL_X, SWIVEL_Y - 0.0175, REEL_Z), 0.026, "SDT_Brass", seg=6)

    drain = MAIN_DRAIN
    a = drain + V(0, -T.MAIN_DRAIN_HOSE, 0)
    fit.clamp(drain + V(0, -(T.MAIN_DRAIN_HOSE - 0.014), 0), V(0, 1, 0), 0.0255)
    b = ports["water_end"]
    # k hrdlu mixéru shora po ose Y těsně u levého okraje (x ~0,01): rám centrály začíná v y -1,77 a x 0,047
    mid = V(b.x + 0.005, b.y + 0.17, (a.z + b.z) / 2)
    P.sweep("Pump_Suction", P.hermite_path([a, mid, b], tangents={0: (0, -1, 0), 2: (0, -1, 0)}, samples=12), 0.025,
            "SDT_HoseBlack", segments=20)

    ip = T.induction_ports(ix, iy, z)
    a = ip["hose_end"] + V(0, -0.030, 0)
    b = ports["conc_end"]
    mids = [V(ix + 0.06, iy + 0.37, hz - 0.20), V(ix + 0.20, iy + 0.44, hz - 0.08)]
    P.sweep("Tank_Induction_Pipe", P.hermite_path([a] + mids + [b], tangents={0: (0, 1, 0), 3: (1, 0, 0)}, samples=12),
            0.025, "SDT_HoseBlack", segments=20)
    fit.finish()


# ---------------------------------------------------------------------------------------------------- šachta baterií
def bay_box():
    sx, sy = BAY_SHAFT
    w = BAY_WALL
    x0, x1 = STRIP_X
    y0, y1 = BAY_Y
    z0 = DECK_TOP + BAY_FEET
    dock = z0 + BAY_DOCK
    top = dock + 0.016 + P.BATTERY_SIZES["S"][0] - 0.03       # nad okraj čouhá horní čelo baterie s madlem
    return x0, x1, y0, y1, z0, dock, top


def bay_cell_x():
    x0, x1 = STRIP_X
    return (x0 + x1) / 2


def build_bay():
    """Šachta na čtyři baterie S (stojí svisle konektorem dolů, nad hranu čouhá horní čelo s madlem), tmavý korpus na
    patkách u levého okraje paluby; u každé šachty pět diod. batterySlotDeck1..4 jsou její děti."""
    vis = bpy.data.objects[ROOT_NAME]
    x0, x1, y0, y1, z0, dock, top = bay_box()
    w = BAY_WALL
    sx, sy = BAY_SHAFT
    cx = bay_cell_x()
    bay = _group("batteryCharger", vis, (cx, (y0 + y1) / 2, DECK_TOP))
    parts = []
    for fx in (x0 + 0.05, x1 - 0.05):
        for fy in (y0 + 0.05, y1 - 0.05):
            parts.append(cylinder_z(f"Charger_Foot_{fx:+.2f}_{fy:+.2f}", (fx, fy, DECK_TOP + BAY_FEET / 2), 0.022,
                                    BAY_FEET, "SDT_Rubber", segments=12))
    parts += [
        box("Charger_Base", x0, x1, y0, y1, z0, dock, "SDT_ChargerGrey"),
        box("Charger_WallFront", x0, x1, y0, y0 + w, dock, top, "SDT_ChargerGrey"),
        box("Charger_WallRear", x0, x1, y1 - w, y1, dock, top, "SDT_ChargerGrey"),
        box("Charger_WallRight", x0, x0 + w, y0 + w, y1 - w, dock, top, "SDT_ChargerGrey"),
        box("Charger_WallLeft", x1 - w, x1, y0 + w, y1 - w, dock, top, "SDT_ChargerGrey"),
    ]
    for i in range(len(BAY_CELLS) - 1):
        ya, yb = BAY_CELLS[i] + sy / 2, BAY_CELLS[i + 1] - sy / 2
        parts.append(box(f"Charger_DividerY{i}", x0 + w, x1 - w, ya, yb, dock, top, "SDT_TankBlack"))
    rim = 0.006
    parts += [
        box("Charger_RimFront", x0, x1, y0, y0 + w, top, top + rim, "SDT_TankBlack"),
        box("Charger_RimRear", x0, x1, y1 - w, y1, top, top + rim, "SDT_TankBlack"),
        box("Charger_RimRight", x0, x0 + w, y0 + w, y1 - w, top, top + rim, "SDT_TankBlack"),
        box("Charger_RimLeft", x1 - w, x1, y0 + w, y1 - w, top, top + rim, "SDT_TankBlack"),
    ]
    for k, cy in enumerate(BAY_CELLS[:BATTERY_COUNT], 1):
        parts.append(box(f"Charger_Dock_{k}", cx - 0.07, cx + 0.07, cy - 0.035, cy + 0.035, dock, dock + 0.006, "SDT_Steel"))
        lx0, lx1 = x1 - w + 0.001, x1 - 0.021        # vnitřní pruh okraje: vnější 2 cm zakrývá stěna pod víkem (Chest_WallLeft)
        parts += charger_leds(k, lx0, lx1, cy, top + rim, 0.02, 0.014)
        _group(f"batterySlotDeck{k}", bay).matrix_world = (
            Matrix.Translation((cx, cy + P.BATTERY_SIZE[2] / 2, dock + 0.016 + P.BATTERY_SIZE[0] / 2)) @ BATTERY_STAND)
    zs =[dock + 0.05 + 0.032 * n for n in range(int((top - dock - 0.12) / 0.032) + 1)]
    for n, zc in enumerate(zs):
        parts.append(box(f"Charger_VentRight_{n}", x0 - 0.006, x0, y0 + 0.06, y1 - 0.06, zc - 0.006, zc + 0.006, "SDT_Mesh"))
    for o in parts:
        _set_parent(o, bay, o.matrix_world.copy())
    return bay


def bay_lid_geometry():
    x0, x1, y0, y1, z0, dock, top = bay_box()
    m = BAY_WALL
    return x0, x1, y0, y1, top + BAY_LID_CLEAR


def build_bay_lid():
    """Víko šachty (chargerLid) na závěsu u vnitřního okraje (osa podél vleku), otevírá se dovnitř pod desku; v i3d otevřené = rozložený
    vlek. Kolem baterií stojí stěny, víko je mělká miska s lemem a madlem na vnitřním okraji. Uzel má základní natočení
    BAY_LID_BASIS (místní osa X = osa závěsu), otevření je natočení kolem místní X."""
    vis = bpy.data.objects[ROOT_NAME]
    x0, x1, y0, y1, zw = bay_lid_geometry()
    t = BAY_LID_T
    x0b, x1b, y0b, y1b, _, _, top = bay_box()
    mat = "SDT_PaintDark"
    cy = (y0 + y1) / 2
    hx, hz = x0 - 0.012, zw + t / 2
    walls = [
        box("Chest_WallFront", x0, x1, y0, y0 + 0.02, top, zw, mat),
        box("Chest_WallRear", x0, x1, y1 - 0.02, y1, top, zw, mat),
        box("Chest_WallRight", x0, x0 + 0.02, y0 + 0.02, y1 - 0.02, top, zw, mat),
        box("Chest_WallLeft", x1 - 0.02, x1, y0 + 0.02, y1 - 0.02, top, zw, mat),
    ]
    sz = DECK_TOP + 0.13
    walls.append(box("Chest_Socket", x1, x1 + 0.02, y0 + 0.10 - 0.035, y0 + 0.10 + 0.035, sz - 0.035, sz + 0.035,
                     "SDT_TankBlack"))
    lid = [
        box("Chest_Lid", x0 - 0.01, x1 + 0.01, y0 - 0.01, y1 + 0.01, zw, zw + t, mat),
        box("Chest_LidLipFront", x0 - 0.01, x1 + 0.01, y0 - 0.01, y0, zw - 0.025, zw, mat),
        box("Chest_LidLipRear", x0 - 0.01, x1 + 0.01, y1, y1 + 0.01, zw - 0.025, zw, mat),
        box("Chest_LidLipOuter", x1, x1 + 0.01, y0, y1, zw - 0.025, zw, mat),
        box("Chest_LidStripe", x1 - 0.055, x1 - 0.03, y0 + 0.05, y1 - 0.05, zw + t, zw + t + 0.002, "SDT_GenOrange"),
        tube("Chest_LidHandle", (x1 + 0.04, cy - 0.07, hz), (x1 + 0.04, cy + 0.07, hz), 0.009, "SDT_Steel", segments=10),
        box("Chest_LidHandlePostA", x1 + 0.01, x1 + 0.04, cy - 0.075, cy - 0.065, hz - 0.009, hz + 0.009, "SDT_Steel"),
        box("Chest_LidHandlePostB", x1 + 0.01, x1 + 0.04, cy + 0.065, cy + 0.075, hz - 0.009, hz + 0.009, "SDT_Steel"),
    ]
    for n, ly in enumerate((y0 + 0.15, y1 - 0.15)):
        lid.append(tube(f"Chest_Hinge{n}", (hx, ly - 0.04, hz), (hx, ly + 0.04, hz), 0.012, "SDT_Steel", segments=10))
    pivot = _group("chargerLid", vis, (hx, cy, hz))
    pivot.rotation_euler = (0, 0, -math.pi / 2)
    bpy.context.view_layer.update()
    for o in walls:
        _set_parent(o, vis, o.matrix_world.copy())
    for o in lid:
        _set_parent(o, pivot, o.matrix_world.copy())
    pivot.rotation_euler = (math.radians(BAY_LID_OPEN_DEG), 0, -math.pi / 2)
    bpy.context.view_layer.update()
    return pivot


def build_charger_cable():
    """Kabel generátor -> zásuvka na šachtě baterií; krátké přímé propojení (šachta je teď hned za centrálou, Pavel
    2026-10-07), ne podél celého boku paluby jako dřív. Pozice zásuvky se čte z už přesunutého Chest_Socket."""
    sock = bpy.data.objects["Chest_Socket"]
    corners = [sock.matrix_world @ Vector(c) for c in sock.bound_box]
    sx = sum(c.x for c in corners) / 8
    sy = sum(c.y for c in corners) / 8
    sz = sum(c.z for c in corners) / 8
    gx, gy, gz = GEN_SOCKET
    # centrála stojí mezi zásuvkou (vpředu) a šachtou (vzadu): kabel ze zástrčky spadne na palubu před rámem centrály (rám od
    # y -2,533, hrana paluby -2,60), po palubě vlevo od ní (mezi rámem centrály x 0,047 a mixérem x 0,017) dozadu, v mezeře mezi
    # šachtou a nádrží (y -1,41 až -1,34) k zásuvce; na palubě ho drží příchytky (dřív visel ~8 cm nad palubou)
    zd = DECK_TOP + CABLE_R + 0.003
    xr, yf, yg = 0.032, -2.565, -1.375
    pts = [(gx, gy, gz), (gx, gy - 0.07, gz), (gx, yf, zd + 0.10), (gx - 0.08, yf, zd), (xr, yf, zd), (xr, yg, zd),
           (sx - 0.16, yg, zd), (sx - 0.08, sy, sz), (sx, sy, sz)]
    path = _rounded_polyline(pts, r=0.05)
    cable = P.sweep("chargerCable", path, CABLE_R, "SDT_HoseBlack", segments=10)
    parts = [
        tube("Charger_Plug", (sx - 0.02, sy, sz), (sx, sy, sz), 0.018, "SDT_Rubber", segments=12, radius_end=0.012),
        tube("Gen_0_ChargePlug", (gx, gy - 0.015, gz), (gx, gy - 0.05, gz), 0.018, "SDT_Rubber", segments=12,
             radius_end=0.012),
    ]
    # příchytky zůstávají na palubě i po odpojení kabelu (animace foldTrailer skryje jen kabel se zástrčkami)
    for n, (cx, cy, along_x) in enumerate(((xr, -2.20, False), (xr, -1.75, False), (0.35, yg, True))):
        a, b = (0.012, CABLE_R + 0.005) if along_x else (CABLE_R + 0.005, 0.012)
        box(f"Charger_CableClipDeck{n}", cx - a, cx + a, cy - b, cy + b, DECK_TOP, zd + CABLE_R + 0.003, "SDT_Steel")
    for o in parts:
        _set_parent(o, cable, o.matrix_world.copy())
    return cable, P.path_length(path)


# ------------------------------------------------------------------------------------------------ bedna na kanystry
def build_hose_reel_parts():
    """Modrý navíječ vpravo za nádrží, osa podél vleku: buben mezi dvěma bočnicemi, konzoly na obou koncích osy, otočný přívod na
    předním konci osy (u nádrže, tam přichází výtlak čerpadla), vodítko hadice a hadice navinutá v jedné vrstvě (fillHoseCoil; konec
    vespod uprostřed zadní bočnice = fillHoseStart, hadice odtud míří stranou ke středu vleku mezi bočnicemi ven)."""
    rx, ry, rz = REEL_X, REEL_Y, REEL_Z
    frame = "SDT_Frame"
    tube("HoseReel_0_Drum", (rx, ry - 0.055, rz), (rx, ry + 0.055, rz), REEL_R_CORE, "SDT_HoseBlue", segments=32)
    for dy in (-0.061, 0.061):
        tube(f"HoseReel_0_Flange{dy:+.2f}", (rx, ry + dy - 0.006, rz), (rx, ry + dy + 0.006, rz), REEL_R_FLANGE, frame, segments=32)
    for side, ya, yb in (("Out", ry + 0.07, ry + 0.082), ("In", ry - 0.082, ry - 0.07)):
        box(f"HoseReel_0_Bracket{side}", rx - 0.05, rx + 0.05, ya, yb, DECK_TOP, rz + 0.04, frame)
    box("HoseReel_0_Base", rx - 0.05, rx + 0.05, ry - 0.082, ry + 0.082, DECK_TOP, DECK_TOP + 0.015, frame)
    tube("HoseReel_0_Axle", (rx, ry - 0.09, rz), (rx, ry + 0.09, rz), 0.02, "SDT_Steel", segments=12)
    tube("HoseReel_0_Swivel", (rx, SWIVEL_Y - 0.0175, rz), (rx, SWIVEL_Y + 0.0175, rz), 0.03, "SDT_Steel", segments=16)
    g = HOSE_R + 0.013
    gx = HOSE_GUIDE_X
    gy = _hose_point_at_x(gx)[1]
    gz = DECK_HOSE_Z
    for n, dy in enumerate((-g, g)):
        box(f"HoseGuide_Post{n}", gx - 0.008, gx + 0.008, gy + dy - 0.006, gy + dy + 0.006, DECK_TOP, gz + 0.045, frame)
    box("HoseGuide_Top", gx - 0.008, gx + 0.008, gy - g - 0.006, gy + g + 0.006, gz + 0.035, gz + 0.045, frame)
    turns = 2 * COIL_HALF / (2 * HOSE_R)
    steps = int(turns * 32)
    coil = []
    for k in range(steps + 1):
        s = k / steps
        a = math.pi + (1 - s) * turns * 2 * math.pi
        coil.append(Vector((rx + COIL_R * math.sin(a), ry - COIL_HALF + 2 * COIL_HALF * s, rz + COIL_R * math.cos(a))))
    P.sweep("fillHoseCoil", coil, HOSE_R, "SDT_HoseBlack", segments=24)


def _descendant_meshes(root):
    out = []
    for o in root.children_recursive:
        if o.type == "MESH" and not o.get("i3D_nonRenderable"):
            out.append(o)
    return out


def mount_drone_on_tray(prefix):
    """Dron ve složené bedně: otočený o DRONE_EXTRA_ROT (šířka vleku místo délky), stopa vystředěná v bedně. Kořen dronu (skript ho při letu
    odpojí a po přistání vrátí pod stejného rodiče) patří pod uzel droneCarrier, který skript při rozložení otočí zpět a posune na plošinu.
    Carrier leží přesně v ose trupu (počátek kořene dronu), takže otáčení kolem jeho osy otáčí dron na místě. Bedna dron zajišťuje sama
    (stěny + plachta), žádné svorky na lyžinách (build_drone_clamps/Clamp_i) se u Mini nestaví - viz build()."""
    root = bpy.data.objects[prefix + "Root"]
    root.rotation_euler.z += DRONE_EXTRA_ROT
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in _descendant_meshes(root) for c in o.bound_box]
    cx = (min(p.x for p in pts) + max(p.x for p in pts)) / 2
    cy = (min(p.y for p in pts) + max(p.y for p in pts)) / 2
    root.location.x += -cx
    root.location.y += DRONE_Y - cy
    bpy.context.view_layer.update()
    carrier = bpy.data.objects["droneCarrier"]
    carrier.location = (root.matrix_world.translation.x, root.matrix_world.translation.y, CRATE_Z0)
    bpy.context.view_layer.update()
    _set_parent(root, carrier, root.matrix_world.copy())
    bpy.context.view_layer.update()


def build_drone_service_parts_mini(prefix):
    """Plnicí hrdlo, lůžko baterie a výřez v trupu staví build_drone_service_parts v SVĚTOVÝCH souřadnicích bez otočení dronu a
    s počátkem dronu v (0, 0), jak to platí u Middle (DRONE_Y = 0). Tady je dron v bedně na DRONE_Y, takže se souřadnice hrdla a baterie
    posunou o DRONE_Y a volá se před otočením dronu (mount_drone_on_tray) - jinak hrdlo viselo mimo trup a výřez řezal vedle něj."""
    global DRONE_FILL_PORT, DRONE_BATTERY
    ports, battery = DRONE_FILL_PORT, DRONE_BATTERY
    DRONE_FILL_PORT = {k: (x, y + DRONE_Y) for k, (x, y) in ports.items()}
    DRONE_BATTERY = {k: (x, y + DRONE_Y) for k, (x, y) in battery.items()}
    try:
        build_drone_service_parts(prefix)
    finally:
        DRONE_FILL_PORT, DRONE_BATTERY = ports, battery


def build_mini_toolbox(suffix="", canister_offset=0):
    """Bedna na 4 kanystry 20 l: tmavý korpus se čtyřmi přihrádkami v řadě, víko se závěsem na hraně u nádrže (toolboxLid,
    otevírá se kladným natočením kolem lokální osy X), uzly toolboxCanister1..4 a toolboxActivateNode. `suffix`/`canister_offset`:
    druhá bedna u levého lemu (uzly toolboxLid2, toolboxActivateNode2, toolboxCanister5..8) s vlastním víkem, aktivací a dialogem;
    staví se na pozici BOX_X = BOX2_X se závěsem na vnější hraně a pak se celá otočí o 180° kolem svého středu (build_equipment),
    takže závěs i otevírání vyjdou zrcadlově k první bedně."""
    vis = bpy.data.objects[ROOT_NAME]
    x0, x1 = BOX_X
    y0, y1 = BOX_Y
    z0 = DECK_TOP
    foot = 0.024
    zb = z0 + foot
    zs = z0 + BOX_H - 0.045
    t = 0.010
    dark = "SDT_PaintDark"
    body = T.Mesh("Toolbox" + suffix)
    inner = T.Mesh("Toolbox_Inner" + suffix)
    hw = T.Mesh("Toolbox_Hardware" + suffix)
    lid = T.Mesh("Toolbox_Lid" + suffix)
    body.box(x0, x1, y0, y1, zb, zb + 0.012, dark, bevel=0.005)
    body.box(x0, x1, y0, y0 + t, zb, zs, dark, bevel=0.004)
    body.box(x0, x1, y1 - t, y1, zb, zs, dark, bevel=0.004)
    body.box(x0, x0 + t, y0 + t, y1 - t, zb, zs, dark, bevel=0.004)
    body.box(x1 - t, x1, y0 + t, y1 - t, zb, zs, dark, bevel=0.004)
    for yy in (y0, y1 - 0.006):
        hw.box(x0 + 0.001, x1 - 0.001, yy, yy + 0.006, zs, zs + 0.004, "SDT_Rubber")
    for xx in (x0, x1 - 0.006):
        hw.box(xx, xx + 0.006, y0 + 0.006, y1 - 0.006, zs, zs + 0.004, "SDT_Rubber")
    floor = zb + 0.012
    inner.box(x0 + t, x1 - t, y0 + t, y1 - t, floor, floor + 0.004, "SDT_Rubber")
    xm = (x0 + x1) / 2
    ys = [(y0 + y1) / 2 + (k - (BOX_SLOTS - 1) / 2) * BOX_PITCH for k in range(BOX_SLOTS)]
    for k in range(BOX_SLOTS - 1):
        yd = (ys[k] + ys[k + 1]) / 2
        inner.box(x0 + t, x1 - t, yd - 0.003, yd + 0.003, floor + 0.004, floor + 0.17, dark)
    # svislá vylisovaná žebra jako bedna Middle/Max (sdt_tanks.build_toolbox); vodorovné panely vypadaly jako šuplíky
    pz0, pz1 = zb + 0.055, zs - 0.055
    xm_ = (x0 + x1) / 2
    for dx in (-0.08, 0.08):
        body.box(xm_ + dx - 0.014, xm_ + dx + 0.014, y1, y1 + 0.004, pz0, pz1, dark, bevel=0.0015)
        body.box(xm_ + dx - 0.014, xm_ + dx + 0.014, y0 - 0.004, y0, pz0, pz1, dark, bevel=0.0015)
    ym = (y0 + y1) / 2
    for dy in (-0.32, -0.22, -0.12, 0.12, 0.22, 0.32):
        body.box(x0 - 0.004, x0, ym + dy - 0.014, ym + dy + 0.014, pz0, pz1, dark, bevel=0.0015)

    # víko z pochozího plechu jako u Middle/Max: miska s lemem dolů, závěs na vnitřním okraji (u nádrže), otevírá se dovnitř pod
    # desku; základní natočení Rz(+90°). Vně dvě západky a jedno madlo na lemu
    hx = x1 + 0.010
    zl = zs + 0.004
    deck = "SDT_TopDeck"
    lid.box(x0 - 0.010, x1 + 0.010, y0 - 0.010, y1 + 0.010, zl, zl + 0.030, deck, bevel=0.004)
    lid.box(x0 - 0.010, x1 + 0.010, y0 - 0.010, y0, zl - 0.040, zl, deck)
    lid.box(x0 - 0.010, x1 + 0.010, y1, y1 + 0.010, zl - 0.040, zl, deck)
    lid.box(x0 - 0.010, x0, y0, y1, zl - 0.040, zl, deck)
    for ry in (ym - 0.30, ym + 0.30):
        lid.box(x0 + 0.03, x1 - 0.03, ry - 0.024, ry + 0.024, zl + 0.030, zl + 0.037, deck, bevel=0.004)
    for yy in (ym - 0.20, ym + 0.20):
        lid.box(x0 - 0.018, x0 - 0.010, yy - 0.025, yy + 0.025, zl - 0.050, zl + 0.010, "SDT_Steel")
        lid.cyl(V(hx, yy - 0.045, zl + 0.012), V(hx, yy + 0.045, zl + 0.012), 0.011, "SDT_Steel", seg=10)
    hz = zl - 0.015
    lid.cyl(V(x0 - 0.034, ym - 0.07, hz), V(x0 - 0.034, ym + 0.07, hz), 0.009, "SDT_Steel", seg=10)
    for dy in (-0.07, 0.07):
        lid.box(x0 - 0.034, x0 - 0.010, ym + dy - 0.006, ym + dy + 0.006, hz - 0.007, hz + 0.007, "SDT_Steel")
    meshes = [m.finish() for m in (body, inner, hw)]
    lid_mesh = lid.finish()
    # štítek čitelný zvenku (od madla): text podél bedny, nahoru = k závěsu
    lw = 0.32
    lh = lw * 52 / 256
    label = P.decal_quad("Decal_LidConc" + suffix, ((x0 + x1) / 2 - lh / 2, ym + lw / 2, zl + 0.030), (0, -1, 0), (1, 0, 0),
                         lw, lh, "boxConc")
    pivot = _group("toolboxLid" + suffix, vis, (hx, ym, zl + 0.012))
    pivot.rotation_euler = (0, 0, math.pi / 2)
    bpy.context.view_layer.update()
    _set_parent(lid_mesh, pivot, lid_mesh.matrix_world.copy())
    _set_parent(label, pivot, label.matrix_world.copy())
    for m in meshes:
        _set_parent(m, vis, m.matrix_world.copy())
    for k, yy in enumerate(ys, 1):
        can = T.build_canister(f"toolboxCanister{k + canister_offset}", Vector((xm, yy, floor + 0.004)))
        can.matrix_world = Matrix.Translation(Vector((xm, yy, floor + 0.004)))
    act = P.empty("toolboxActivateNode" + suffix, Vector((xm, (y0 + y1) / 2, zs + 0.20)))
    act.empty_display_size = 0.10
    return pivot


# ---------------------------------------------------------------------------------------------------- elektrocentrála
def gen_matrix():
    gx, gy = GEN_POS
    return Matrix.Translation((gx, gy, 0)) @ Matrix.Rotation(GEN_ROT, 4, "Z") @ Matrix.Translation((-gx, -gy, 0))


def build_rotated_generator(z):
    """Centrála z sdt_generator, po postavení otočená kolem svislé osy středu půdorysu (GEN_ROT): panel s ovladači míří
    dopředu, hrdlo nádrže je vlevo vpředu mimo přistávací desku. Vrací polohu hrdla a ústí výfuku po otočení."""
    before = set(bpy.data.objects.keys())
    gen = G.build_generator(GEN_POS, z, GEN_SOCKET_LOCAL)
    bpy.context.view_layer.update()
    m = gen_matrix()
    root = P._root
    new = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
    for o in new:
        if o.parent is None or o.parent is root:
            o.matrix_world = m @ o.matrix_world
    bpy.context.view_layer.update()
    return {"cap": m @ Vector(gen["cap"]), "exhaust": m @ Vector(gen["exhaust"])}


# ---------------------------------------------------------------------------------------------------------- bedna na dron
# Tři ploché panely P (přední stěna) - H (horní víko) - Z (zadní stěna) zavěšené na sobě přes čepy padHingeP/H/Z
# (stejný trik jako u staré padFlap: každý panel je POSTAVEN NAPLOCHO v "rozloženém" tvaru - panelP od padHingeP dál
# v +Y, panelH od padHingeH dál, panelZ od padHingeZ dál -, teprve pak se čepu nastaví STOŽENÁ rotace a hierarchie
# panel poskládá do bedny). Tři čepy jedou kolem stejné osy X, takže se úhly v hierarchii sčítají: se stejnou rotací
# (90° složeno .. 0° rozloženo) na každém čepu vyjde přesně bedna (Z nahoru, H do strany, P dolů). V i3d (tahle funkce) se staví
# STOŽENÝ stav; rozkládání za běhu dělá SprayDronePad.lua.
CRATE_LEG_REST = 0.02                       # délka vysunutelné části nožičky v modelu (skript ji natahuje měřítkem)
CRATE_LEG_HOUSE = 0.10                      # hloubka pouzdra nožičky
CRATE_LEG_FOOT = 0.025                      # délka patky pod koncem tyče (viz _crate_leg)
CRATE_MAX_LEG_LENGTH = 1.0                  # nejdelší vysunutí nožičky (m), export_mini_mod.pad_values
CRATE_MAX_HEIGHT_DIFF = 0.5                 # největší výškový rozdíl terénu pod nožičkami (m)
CRATE_CHECK_HEIGHT = 1.2                    # volný prostor nad rozloženou plošinou, který musí být volný (m)
CRATE_LIFT = 0.12                           # o kolik se dron nadzvedne nad plošinu, když se po rozložení bedny otáčí a jede na její střed (m)
CRATE_SETTLE = -0.011                         # o kolik níž dron dosedne na rozloženou plošinu než stál ve složené bedně (m): záporné = výš, lyžiny sedí
                                            # na čarách písmene H (3 mm nad plechem plošiny + 3 mm kruh)
HELI_PAD_R = 0.64                           # poloměr heliportu na prostředním panelu (panel je 1,346 m hluboký)
HELI_PAD_RING = (0.56, 0.62)
HELI_PAD_H = (0.84, 0.62, 0.10)             # šířka (příčně), výška (podél vleku), tloušťka čar písmene H: ramena ven za trup a lyžiny dronu


def _crate_panel(name, y_from, length, kind):
    """Panel postavený naplocho (world prostor, jako zbytek souboru) od y_from do y_from+length na CRATE_Z0;
    volající ho pak _set_parent() na čep, který ho teprve rotací složí do bedny. y_from = světová souřadnice
    čepu, na který se panel věší (_group() tady bere world pozici, ne lokální offset od rodiče).
    Horní strana (uvnitř bedny, pochozí) je pochozí plech, spodní strana (ve složené bedně VENKU) zelený lak s černým lemem, žebry,
    kloubovými válečky na čepech, zámky a rohovými patkami. kind: "Z" zadní stěna, "H" střecha, "P" přední stěna (v její spodní hraně
    ve složeném stavu je výřez pro hadici)."""
    hx, t, z0 = CRATE_HX, CRATE_WALL_T, CRATE_Z0
    y1 = y_from + length
    zb = z0 - t / 2
    rim_w, rim_h = 0.04, 0.022
    frame, steel, green = "SDT_Frame", "SDT_Steel", "SDT_CrateGreen"
    m = T.Mesh(name)

    def plate(ya, yb, xa, xb):
        m.box(xa, xb, ya, yb, z0, z0 + t / 2, "SDT_TopDeck")
        m.box(xa, xb, ya, yb, zb, z0, green)

    notch = None
    if kind == "P":
        nx = _hose_x_at_y(CRATE_FRONT_Y)
        notch = (nx - HOSE_NOTCH_W / 2, nx + HOSE_NOTCH_W / 2)
        plate(y_from, y1 - HOSE_NOTCH_L, -hx, hx)
        plate(y1 - HOSE_NOTCH_L, y1, -hx, notch[0])
        plate(y1 - HOSE_NOTCH_L, y1, notch[1], hx)
    else:
        plate(y_from, y1, -hx, hx)

    for sx in (-1, 1):
        xa, xb = sorted((sx * hx, sx * (hx - rim_w)))
        m.box(xa, xb, y_from, y1, zb - rim_h, zb, frame, bevel=0.003)
    if kind == "Z":
        m.box(-hx + rim_w, hx - rim_w, y_from, y_from + rim_w, zb - rim_h, zb, frame, bevel=0.003)
    elif kind == "P":
        m.box(-hx + rim_w, notch[0], y1 - rim_w, y1, zb - rim_h, zb, frame, bevel=0.003)
        m.box(notch[1], hx - rim_w, y1 - rim_w, y1, zb - rim_h, zb, frame, bevel=0.003)
    for xr in (-0.55, 0.0, 0.55):
        m.box(xr - 0.025, xr + 0.025, y_from + 0.07, y1 - 0.07, zb - 0.012, zb, green, bevel=0.004)

    hinges = {"Z": (y1,), "H": (y1,), "P": ()}[kind]
    for yh in hinges:
        for xk in (-0.60, 0.0, 0.60):
            m.cyl(V(xk - 0.13, yh, z0), V(xk + 0.13, yh, z0), 0.017, steel, seg=10)

    def hasp(xc, yc):
        m.box(xc - 0.025, xc + 0.025, yc - 0.045, yc + 0.045, zb - 0.012, zb, steel, bevel=0.002)
        m.box(xc - 0.015, xc + 0.015, yc - 0.015, yc + 0.015, zb - 0.026, zb - 0.012, frame, bevel=0.002)

    if kind == "P":
        for xc in (-0.68, 0.68):
            hasp(xc, y1 - 0.17)
        for xp in (0.12, 0.42):
            m.box(xp - 0.01, xp + 0.01, y1 - 0.26, y1 - 0.24, zb - 0.045, zb, steel)
        m.cyl(V(0.12, y1 - 0.25, zb - 0.045), V(0.42, y1 - 0.25, zb - 0.045), 0.009, steel, seg=10)
    if kind == "Z":
        for xc in (-0.68, 0.68):
            hasp(xc, y_from + 0.17)
    if kind in ("Z", "P"):
        yc = y_from + 0.045 if kind == "Z" else y1 - 0.045
        for sx in (-1, 1):
            m.box(sx * (hx - 0.045) - 0.045, sx * (hx - 0.045) + 0.045, yc - 0.045, yc + 0.045, zb - rim_h - 0.012, zb - rim_h, frame,
                  bevel=0.006)
    return m.finish()


HOSE_NOTCH_W, HOSE_NOTCH_L = 0.11, 0.07     # výřez v přední stěně bedny (při jejím spodním okraji) pro hadici: šířka a hloubka


def _crate_leg(suffix, parent, lx, ly):
    """Nožička zavěšená na konci panelu (pouzdro + vysunutelná tyč padLegRod<suffix> + patka padLegFoot<suffix>,
    stejný princip jako dřívější padLeg u desky): v klidu (i3d) zasunutá, SprayDronePad.lua ji za běhu natahuje. Pouzdro je potomek uzlu
    padLeg<suffix>, takže se ve složené bedně neukáže (skript uzel skryje a při dorozložení plynule zvětší).
    lx, ly jsou světové souřadnice čepu `parent` v klidové (rozložené) referenční poloze."""
    z0 = CRATE_Z0
    frame = "SDT_Frame"
    leg = _group(f"padLeg{suffix}", parent, (lx, ly, z0))
    sleeve = box(f"Crate_LegSleeve{suffix}", lx - 0.08, lx + 0.08, ly - 0.08, ly + 0.08, z0 - CRATE_LEG_HOUSE, z0, frame)
    _set_parent(sleeve, leg, sleeve.matrix_world.copy())
    rod = T.Mesh(f"padLegRod{suffix}")
    rod.cyl(V(lx, ly, z0), V(lx, ly, z0 - CRATE_LEG_REST), 0.022, "SDT_Steel", seg=12)
    rod_obj = rod.finish()
    T.attach(rod_obj, leg, (lx, ly, z0))
    zf = z0 - CRATE_LEG_REST
    foot = T.Mesh(f"padLegFoot{suffix}")
    foot.cyl(V(lx, ly, zf - CRATE_LEG_FOOT), V(lx, ly, zf), 0.07, "SDT_Rubber", seg=16)
    foot_obj = foot.finish()
    T.attach(foot_obj, leg, (lx, ly, zf))


# ------------------------------------------------------------------------------------ boční stěny a polepy bedny na dron
# Boční stěny bedny (Pavel 2026-10-11, místo dřívějších plachet): plechové panely stojící na hraně paluby mezi přední (P) a zadní (Z)
# stěnou pod střechou H. Čep padSideL/R leží na vnější spodní hraně u lemu paluby (osa podél vleku); při rozložení se panel vyklopí ven
# a sklopí k zemi (SprayDronePad.applyPose, úhel se v Lua dorovná podle terénu), vnitřní strana (pochozí plech SDT_TopDeck v rámu) je pak
# nahoře. Panel není potomkem čepů střechy ani dronu, takže mu nic z pohybu bedny nepřekáží.
SIDE_PIVOT_Z = DECK_TOP + 0.0125            # čep s kloubovými válečky leží na lemu paluby, spodek panelu = pivot
SIDE_H = CRATE_H - 0.012 - 0.014            # výška panelu: pod střechou zbývá 14 mm
SIDE_Y = (CRATE_FRONT_Y + 0.016, CRATE_Y_ANCHOR - 0.016)   # délka mezi přední a zadní stěnou
SIDE_PLATE = 0.006                          # jedna vrstva plechu (venku zelený lak, uvnitř pochozí plech)
SIDE_RIM = 0.034                            # lem z vnitřní strany (po vyklopení rám pochozí plochy)
SIDE_FALL_DEG = 150.0                       # úhel vyklopení v modelu a v náhledech (Lua ho dorovná podle terénu); 150° = spodní hrana u země


# Polepy značky (Pavel 2026-10-15, místo dřívější identity SPRAY DRONE z geometrie): lockup designu z atlasu sdt_brand
# (sdt_parts.brand_decal_set, uzly brand_<KEY>_<místo>, export z nich udělá konfiguraci Design) a pod ním pruh v barvě designu.
# Vně bedny leží lockup přímo na bedně, bez štítku (Pavel 2026-10-15): barva bedny (SDT_CrateGreen) se v obchodě mění, proto jsou
# tam dvě sady (lockupOnDark / lockupOnLight pod brand_tone_group) a konfigurace barvy ukáže tu čitelnou. Pochozí plech uvnitř
# barvu nemění a je světlý, tam jde rovnou lockupOnLight.
BL = P.BL
BRAND_GAP, BRAND_STRIPE = 0.06, 0.08        # mezera pod lockupem a výška pruhu (podíl výšky obsahu lockupu), jako schválený náhled
BRAND_BACKING_T = 0.002                     # tloušťka štítku
BRAND_BACKING_R = 0.025                     # zaoblení rohů štítku


def _brand_backing(name, center, normal, up, u0, u1, v0, v1, parent, mat="SDT_PaintDark"):
    """Štítek pod polepem: zaoblený obdélník u0..u1 x v0..v1 v rovině polepu kolem center, tloušťka BRAND_BACKING_T ven."""
    u, v, n = P._face_frame(normal, up)
    r = BRAND_BACKING_R
    pts = []
    for cu, cv, a0 in ((u1 - r, v1 - r, 0), (u0 + r, v1 - r, 90), (u0 + r, v0 + r, 180), (u1 - r, v0 + r, 270)):
        for k in range(5):
            a = math.radians(a0 + 22.5 * k)
            pts.append(u * (cu + r * math.cos(a)) + v * (cv + r * math.sin(a)))
    bm = bmesh.new()
    lo = [bm.verts.new(p) for p in pts]
    hi = [bm.verts.new(p + n * BRAND_BACKING_T) for p in pts]
    bm.faces.new(hi)
    bm.faces.new(list(reversed(lo)))
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    obj = P._finish(name, bm, Matrix.Translation(Vector(center)), mat)
    return P._keep_world(obj, parent)


def brand_block(place, kind, center, normal, up, h, fit_w, parent, tone=False, offset=0.0015):
    """Lockup každého designu se středem obsahu v center (bod na povrchu, ve světě) a pod ním pruh, bez štítku.
    h = výška obsahu lockupu, fit_w = největší šířka celku; delší nápis (STRATUS AGRI) se do ní zmenší, ostatní designy mají
    stejnou výšku. Z oblasti atlasu se bere jen obsah bez průhledného okraje, ať se polepy navzájem nepřekrývají.
    tone = plocha v barvě bedny: dvě sady (lockupOnDark / lockupOnLight, P.brand_tone_group), barva bedny vybere jednu."""
    if tone:
        for t, k in (("Dark", "lockupOnDark"), ("Light", "lockupOnLight")):
            tg = P.brand_tone_group(place, t, parent, center)
            brand_block(place + t, k, center, normal, up, h, fit_w, tg, offset=offset)
            if t == "Light":
                P._hide_tree(tg, True)
        return
    u, v, n = P._face_frame(normal, up)
    c = Vector(center)
    for key in BL.DESIGN_ORDER:
        cw, ch = BL.LOCKUP_CONTENT[key]
        reg = min(4 * h / ch, fit_w / cw)    # šířka celé oblasti 4 : 1
        w, hc = reg * cw, reg / 4 * ch
        fw, fh = min(1.0, cw + 0.02), min(1.0, ch + 0.04)
        P.brand_decal_set(place, kind, c, n, v, reg * fw, reg / 4 * fh, parent, offset, designs=(key,),
                          sub=((1 - fw) / 2, (1 - fh) / 2, (1 + fw) / 2, (1 + fh) / 2))
        gap, sh = BRAND_GAP * hc, BRAND_STRIPE * hc
        P.brand_decal_set(place, "stripe", c - v * (hc / 2 + gap + sh / 2), n, v, w, sh, parent, offset, designs=(key,))
        print(f"polep {place} {key}: {w:.3f} x {hc:.3f} m")


def brand_mark(place, center, normal, up, size, parent):
    """Samotný znak designu na světlém čtvercovém štítku (na tmavém podkladu by tmavý znak STRATUS AGRI zanikl)."""
    m = 0.12 * size
    for key in BL.DESIGN_ORDER:
        g = P.brand_group(key, place, parent, center)
        P.brand_decal_set(place, "mark", center, normal, up, size, parent=parent, offset=BRAND_BACKING_T + 0.0015, designs=(key,))
        b = _brand_backing(f"BrandBacking_{place}_{key}", center, normal, up, -size / 2 - m, size / 2 + m, -size / 2 - m, size / 2 + m, g,
                           "SDT_PaintWhite")
        b.hide_render = g.hide_render


def _panel_frame(origin, u, v, n):
    """pos(a, b, off) pro polep na ploše s počátkem origin, osami čtení u (vpravo), nahoru v a ven n (světové souřadnice)."""
    origin, u, v, n = Vector(origin), Vector(u), Vector(v), Vector(n)
    return lambda a, b, off=0.0: origin + u * a + v * b + n * off


def _decal_on(name, pos, width, height, region, parent, sub=None, offset=0.0):
    """Nálepka z atlasu na ploše daného rámu (pos): vystředěná vodorovně v počátku rámu, spodní hrana na b = 0, rozměr width x height."""
    c = pos(-width / 2, 0, offset)
    u = pos(1, 0, 0) - pos(0, 0, 0)
    v = pos(0, 1, 0) - pos(0, 0, 0)
    obj = P.decal_quad(name, c, u, v, width, height, region, sub, offset=0.0)
    _set_parent(obj, parent, obj.matrix_world.copy())
    return obj


def _stripe_decal(name, pos, width, height, parent, offset=0.0):
    """Výstražné šikmé pruhy (oblast stripe atlasu, 16 : 1); u užšího pásu se oblast ořízne, ať se vzor neroztahuje."""
    return _decal_on(name, pos, width, height, "stripe", parent, (0.0, 0.0, min(1.0, width / height / 16.0), 1.0), offset)


def _text_decal(name, pos, width, region, aspect, parent, sub=None, offset=0.0):
    return _decal_on(name, pos, width, width / aspect, region, parent, sub, offset)


def build_side_panels():
    """Dvě boční stěny (padSideL / padSideR): zelený plech venku, pochozí plech v rámu uvnitř, vnější výztuhy, kloubové válečky na čepu."""
    vis = bpy.data.objects[ROOT_NAME]
    y0, y1 = SIDE_Y
    yc = (y0 + y1) / 2
    z0, z1 = SIDE_PIVOT_Z, SIDE_PIVOT_Z + SIDE_H
    t = SIDE_PLATE
    pivots = {}
    for name, sx in (("L", 1), ("R", -1)):
        xo = sx * CRATE_HX
        pivot = _group(f"padSide{name}", vis, (xo, yc, z0))
        pivot.empty_display_size = 0.06

        def X(d):
            return xo - sx * d                        # d > 0 dovnitř od vnějšího líce (čepu)

        parts = [
            box(f"Crate_Side{name}", X(0), X(t), y0, y1, z0, z1, "SDT_CrateGreen"),
            box(f"Crate_SideDeck{name}", X(t), X(2 * t), y0, y1, z0, z1, "SDT_TopDeck"),
        ]
        rw, rh = SIDE_RIM, SIDE_RIM - 2 * t
        for tag, (ya, yb, za, zb, mat) in {
            "Bottom": (y0, y1, z0, z0 + rw, "SDT_Frame"), "Top": (y0, y1, z1 - rw, z1, "SDT_Rubber"),
            "Front": (y0, y0 + rw, z0 + rw, z1 - rw, "SDT_Frame"), "Rear": (y1 - rw, y1, z0 + rw, z1 - rw, "SDT_Frame"),
        }.items():
            parts.append(box(f"Crate_SideRim{tag}{name}", X(2 * t), X(2 * t + rh), ya, yb, za, zb, mat))
        for k, dy in enumerate((-0.55, 0.55)):
            parts.append(box(f"Crate_SideRib{name}{k}", X(0), X(-0.008), yc + dy - 0.022, yc + dy + 0.022, z0 + 0.03, z1 - 0.03,
                             "SDT_Frame"))
        for k, dy in enumerate((-0.50, 0.0, 0.50)):
            parts.append(tube(f"Crate_SideKnuckle{name}{k}", (xo, yc + dy - 0.10, z0), (xo, yc + dy + 0.10, z0), 0.012, "SDT_Steel",
                              segments=10))
        for k, dy in enumerate((-0.50, 0.50)):
            parts.append(box(f"Crate_SideHasp{name}{k}", X(-0.008), X(-0.012), yc + dy - 0.03, yc + dy + 0.03, z1 - 0.10, z1 - 0.06,
                             "SDT_Steel"))
        for o in parts:
            _set_parent(o, pivot, o.matrix_world.copy())
        pivots[name] = pivot
    return pivots


def decorate_side_panels(pivots):
    """Polepy bočních stěn. Venku lockup designu s pruhem přímo na stěně mezi výztuhami, výstražné pruhy při horní hraně a štítek SD-S;
    uvnitř (po vyklopení pochozí plocha nahoře) lockupOnLight mezi čepem a pochozím pruhem, čte se zvenku od vyklopené stěny
    (horní hrana textu k čepu, tedy k vleku)."""
    y0, y1 = SIDE_Y
    yc = (y0 + y1) / 2
    z0 = SIDE_PIVOT_Z
    for name, pivot in pivots.items():
        sx = 1 if name == "L" else -1
        xo = sx * CRATE_HX

        def frame(dy=0.0, dz=0.0):
            return _panel_frame((xo, yc + sx * dy, z0 + dz), (0, sx, 0), (0, 0, 1), (sx, 0, 0))

        brand_block(f"crate{name}", "lockupOnDark", (xo, yc, z0 + 0.458), (sx, 0, 0), (0, 0, 1), 0.34, 1.0, pivot, tone=True)
        _stripe_decal(f"Decal_SideStripe{name}", frame(0.0, SIDE_H - 0.105), 0.96, 0.06, pivot, offset=0.0028)
        _text_decal(f"Decal_SideTag{name}", frame(0.0, 0.045), 0.26, "droneS", 4.0, pivot, offset=0.0028)
        xi = xo - sx * (2 * SIDE_PLATE)
        walk = _panel_frame((xi, yc, z0 + SIDE_H - 0.20), (0, -sx, 0), (0, 0, 1), (-sx, 0, 0))
        _stripe_decal(f"Decal_SideWalk{name}", walk, 1.0, 0.10, pivot, offset=0.0015)
        brand_block(f"crateIn{name}", "lockupOnLight", (xi, yc, z0 + 0.25), (-sx, 0, 0), (0, 0, -1), 0.28, 1.10, pivot)


def decorate_crate_panels(hingeZ, hingeH, hingeP, y0, y1, y2):
    """Výstražné pruhy na vnější straně panelů bedny (panely se staví v rozložené poloze, jejich spodní strana je vnější stranou
    složené bedny; pruh leží 1,5 mm nad žebry) a menší polep značky na pochozí ploše přední stěny P, která je po rozložení konec
    plošiny za heliportem (čte se od konce plošiny, horní hrana textu k vleku). Polepy značky vně bedny: brand_crate_outside."""
    zs = CRATE_Z0 - CRATE_WALL_T / 2 - 0.0135
    n = (0, 0, -1)
    fz = lambda b=0.0, a=0.0: _panel_frame((a, y0 + b, zs), (-1, 0, 0), (0, 1, 0), n)
    _stripe_decal("Decal_StripeZ", fz(0.04), 1.60, 0.10, hingeZ)
    fh = lambda b=0.0, a=0.0: _panel_frame((a, y1 + b, zs), (-1, 0, 0), (0, 1, 0), n)
    _stripe_decal("Decal_StripeH", fh(CRATE_LH - 0.15), 1.60, 0.10, hingeH)
    fp = lambda b=0.0, a=0.0: _panel_frame((a, y2 + CRATE_H - b, zs), (1, 0, 0), (0, -1, 0), n)
    _stripe_decal("Decal_StripeP", fp(0.16), 1.30, 0.10, hingeP)
    brand_block("padDeck", "lockupOnLight", (0, y2 + CRATE_H / 2 - 0.02, CRATE_Z0 + CRATE_WALL_T / 2), (0, 0, 1), (0, -1, 0), 0.20, 1.2,
                hingeP)


def brand_crate_outside(hingeZ, hingeH, hingeP):
    """Polepy značky na vnější straně složené bedny (Pavel 2026-10-15, tabulka umístění z tmp/polep_mini): zadní stěna Z, čelo P nad
    madlem a výstražným pruhem, víko H (čte se zezadu, horní hrana textu k oji). Staví se až ve složené poloze (souřadnice ve světě,
    polep visí pod čepem panelu a jede s ním); polep leží na žebrech panelu (CRATE_WALL_T / 2 + 12 mm od roviny čepu)."""
    d = CRATE_WALL_T / 2 + 0.012
    z0 = CRATE_Z0
    brand_block("crateZ", "lockupOnDark", (0, CRATE_Y_ANCHOR + d, z0 + 0.55), (0, 1, 0), (0, 0, 1), 0.40, 1.74, hingeZ, tone=True)
    brand_block("crateP", "lockupOnDark", (0, CRATE_FRONT_Y - d, z0 + 0.585), (0, -1, 0), (0, 0, 1), 0.36, 1.74, hingeP, tone=True)
    brand_block("crateH", "lockupOnDark", (0, CRATE_Y_ANCHOR - 0.64, z0 + CRATE_H + d), (0, 0, 1), (0, -1, 0), 0.50, 1.74, hingeH,
                tone=True)


def build_pad_heliport(hinge, y1):
    """Heliport na prostředním panelu (H), na který dron po rozložení bedny dosedne: tmavý kruh, bílé mezikruží a písmeno H s rameny
    podél vleku, tak velké, že ramena H i lyžiny dronu zůstanou vidět vedle trupu. Staví se v rozložené (ploché) referenční poloze,
    stejně jako panely; vrstvy mají decalLayer jako heliport Middle (build_heliport). Ve složené bedně leží uvnitř střechy."""
    cx, cy = 0.0, y1 + CRATE_LH / 2
    z = CRATE_Z0 + CRATE_WALL_T / 2
    t = HELI_LAYER
    disk = cylinder_z("Heliport_Disk", (cx, cy, z + t / 2), HELI_PAD_R, t, "SDT_PaintDark", segments=64)
    ring = P.ring_z("Heliport_Ring", (cx, cy, z + 1.5 * t), *HELI_PAD_RING, t, "SDT_PaintWhite", segments=64)
    w, h, s = HELI_PAD_H
    z0, z1 = z + t, z + 2 * t
    marks = [
        box("Heliport_H_L", cx + w / 2 - s, cx + w / 2, cy - h / 2, cy + h / 2, z0, z1, "SDT_PaintWhite"),
        box("Heliport_H_R", cx - w / 2, cx - w / 2 + s, cy - h / 2, cy + h / 2, z0, z1, "SDT_PaintWhite"),
        box("Heliport_H_Bar", cx - w / 2 + s, cx + w / 2 - s, cy - s / 2, cy + s / 2, z0, z1, "SDT_PaintWhite"),
    ]
    for o, layer in [(disk, 1), (ring, 2)] + [(m, 2) for m in marks]:
        _physics(o, decalLayer=layer)
        _set_parent(o, hinge, o.matrix_world.copy())


def build_pad_crate():
    """Bedna 1,86 x 1,35 x 0,85 m (celá šířka vleku) nad dronem na konci paluby. Dron sedí přímo na palubě (uzel droneCarrier),
    otočený o DRONE_EXTRA_ROT navíc - viz mount_drone_on_tray(). Řetěz čepů padHingeZ -> padHingeH -> padHingeP drží panely Z/H/P; SprayDronePad.lua je za běhu rozloží
    do jedné roviny (samostatná plošina na nožičkách padLeg1..6, nemusí se dál dotýkat vleku) a dron na ni přistane
    doprostřed. Postup (viz hlavička souboru výš): panely i čepy se postaví v "klidové" referenční poloze, jako by
    byly rozložené v rovné řadě od CRATE_Y_ANCHOR dál (+Y) - teprve na konci se čepům nastaví 90° a hierarchie je
    složí do bedny. `_group()`/`box()` v tomhle souboru berou SVĚTOVÉ souřadnice, ne lokální offset od rodiče."""
    y0 = CRATE_Y_ANCHOR
    anchor = _group("padAnchor", bpy.data.objects[ROOT_NAME], (0, y0, CRATE_Z0))
    hingeZ = _group("padHingeZ", anchor, (0, y0, CRATE_Z0))
    panelZ = _crate_panel("Crate_PanelZ", y0, CRATE_H, "Z")
    _set_parent(panelZ, hingeZ, panelZ.matrix_world.copy())

    y1 = y0 + CRATE_H
    hingeH = _group("padHingeH", hingeZ, (0, y1, CRATE_Z0))
    panelH = _crate_panel("Crate_PanelH", y1, CRATE_LH, "H")
    _set_parent(panelH, hingeH, panelH.matrix_world.copy())

    y2 = y1 + CRATE_LH
    hingeP = _group("padHingeP", hingeH, (0, y2, CRATE_Z0))
    panelP = _crate_panel("Crate_PanelP", y2, CRATE_H, "P")
    _set_parent(panelP, hingeP, panelP.matrix_world.copy())

    y3 = y2 + CRATE_H
    hingeEnd = _group("padHingeEnd", hingeP, (0, y3, CRATE_Z0))   # konec plošiny po rozložení (reference pro Lua)

    # kolize panelů: deska 6 cm kolem každého panelu v rozložené (referenční) poloze, na stejném čepu jako panel, takže se složí do bedny
    # a po rozložení tvoří pochozí plošinu (Pavel 2026-10-13: propadá se skrz). Jména colPad* hledá SprayDroneStation.updateFreeze.
    for tag, hinge, ya, length in (("Z", hingeZ, y0, CRATE_H), ("H", hingeH, y1, CRATE_LH), ("P", hingeP, y2, CRATE_H)):
        _shape_box(f"colPad{tag}", hinge, -CRATE_HX, CRATE_HX, ya, ya + length, CRATE_Z0 - 0.03, CRATE_Z0 + 0.03, COL_VEHICLE,
                   compoundChild=True, density=0.001)

    leg_x = CRATE_HX - 0.09
    _crate_leg(1, hingeH, -leg_x, y1)
    _crate_leg(2, hingeH, leg_x, y1)
    _crate_leg(3, hingeP, -leg_x, y2)
    _crate_leg(4, hingeP, leg_x, y2)
    _crate_leg(5, hingeEnd, -leg_x, y3)
    _crate_leg(6, hingeEnd, leg_x, y3)

    build_pad_heliport(hingeH, y1)
    decorate_crate_panels(hingeZ, hingeH, hingeP, y0, y1, y2)

    for h in (hingeZ, hingeH, hingeP):
        h.rotation_euler = (math.pi / 2, 0, 0)        # složený stav (viz hlavička funkce)

    _group("droneCarrier", bpy.data.objects[ROOT_NAME], (0, DRONE_Y, CRATE_Z0))    # přesné místo dostane v mount_drone_on_tray
    bpy.context.view_layer.update()
    brand_crate_outside(hingeZ, hingeH, hingeP)
    sides = build_side_panels()
    decorate_side_panels(sides)


CAR_COUPLER_Y = -3.55
_big_build_coupler = build_coupler


def build_coupler(tip):
    """Hlava spojky, nájezdová brzda a kabel mají ve velkém skriptu pevné souřadnice pro oj velkého vleku: postaví se v jeho
    rámci (spojka -3,55, čelo vleku o stejný posun blíž) a celé se posunou k hrotu delší oje."""
    global BASE_Y0, COUPLER_Y
    dy = COUPLER_Y - CAR_COUPLER_Y
    mine = BASE_Y0, COUPLER_Y
    BASE_Y0, COUPLER_Y = BASE_Y0 - dy, CAR_COUPLER_Y
    before = set(bpy.data.objects.keys())
    try:
        _big_build_coupler(Vector((tip.x, tip.y - dy, tip.z)))
    finally:
        BASE_Y0, COUPLER_Y = mine
    bpy.context.view_layer.update()
    shift = Matrix.Translation((0, dy, 0))
    for name in [n for n in bpy.data.objects.keys() if n not in before]:
        o = bpy.data.objects[name]
        o.matrix_world = shift @ o.matrix_world


_big_build_chassis = build_chassis


def build_chassis():
    """Podvozek velkého vleku (hnědá paluba po celé délce, rámem i zadním nosníkem) s listovým pružením místo ramen."""
    _big_build_chassis()
    build_suspension()


LEAF_X = 0.70                               # poloha pružin v ose X (blíž ke kolům, pod deskou paluby)
LEAF_HALF = 0.34                            # polovina délky hlavního listu (zadní úchyt je ještě pod koncem paluby)


def build_suspension():
    """Listové pružení místo ramen: hranatá náprava, na ní pod rámem na každé straně svazek pěti listů (nejdelší nahoře,
    oka a třmeny na koncích, úchyty k rámu), třmenové šrouby s přítlačnou deskou, brzdový buben u kola a náboj."""
    for name in [o.name for o in bpy.data.objects if o.name.startswith(("Axle_", "SwingArm_", "Hanger_"))]:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    ay = AXLE_Y[0]
    frame = "SDT_Frame"
    steel = "SDT_Steel"
    axle_top = WHEEL_R + 0.035
    stub = TRACK_X - WHEEL_W / 2 - 0.07                 # konec nápravy těsně u brzdového bubnu, který stojí hned za pneu
    box("Axle_1", -stub, stub, ay - 0.035, ay + 0.035, WHEEL_R - 0.035, axle_top, frame)
    leaf_t, leaf_gap = 0.010, 0.012
    z_main = axle_top + 4 * leaf_gap + leaf_t
    z_below = DECK_TOP - DECK_PLATE
    rise = 0.095
    for side, sx in (("L", 1), ("R", -1)):
        xs = sx * LEAF_X
        for k, half in enumerate((LEAF_HALF, 0.28, 0.22, 0.16, 0.10)):
            stations = []
            for i in range(9):
                u = -1 + i / 4
                y = ay + half * u
                yy = (y - ay) / LEAF_HALF
                top = z_main + rise * yy * yy - k * leaf_gap
                stations.append((y, 0.030, top - leaf_t, top, 8))
            P.loft_y(f"Leaf_{side}{k}", stations, steel, x=xs, segments=12)
        top_c = z_main
        box(f"LeafSeat_{side}", xs - 0.045, xs + 0.045, ay - 0.075, ay + 0.075, top_c, top_c + 0.014, frame)
        box(f"LeafClamp_{side}", xs - 0.05, xs + 0.05, ay - 0.07, ay + 0.07, WHEEL_R - 0.035 - 0.014, WHEEL_R - 0.035, frame)
        for dy in (-0.045, 0.045):
            for dx in (-0.034, 0.034):
                tube(f"UBolt_{side}{dx:+.2f}{dy:+.2f}", (xs + dx, ay + dy, WHEEL_R - 0.055), (xs + dx, ay + dy, top_c + 0.034),
                     0.007, steel, segments=8)
        for e in (-1, 1):
            yc = ay + e * LEAF_HALF
            eye_z = z_main + rise
            tube(f"LeafEye_{side}{e:+d}", (xs - 0.034, yc, eye_z - leaf_t / 2), (xs + 0.034, yc, eye_z - leaf_t / 2), 0.016, steel,
                 segments=12)
            for dx in (-0.044, 0.044):
                box(f"LeafHanger_{side}{e:+d}{dx:+.2f}", xs + dx - 0.004, xs + dx + 0.004, yc - 0.025 - (0.0 if e < 0 else 0.0),
                    yc + 0.025, eye_z - 0.02, z_below, frame)
        side_rear = ay + LEAF_HALF
        box(f"LeafShackleBar_{side}", xs - 0.044, xs + 0.044, side_rear + 0.02, side_rear + 0.026, z_main + rise - 0.02,
            z_main + rise + 0.03, steel)
        cylinder_x(f"BrakeDrum_{side}", (sx * (TRACK_X - WHEEL_W / 2 - 0.03), ay, WHEEL_R), 0.11, 0.05, "SDT_CastIron", segments=24)
        cylinder_x(f"Hub_{side}", (sx * (TRACK_X - WHEEL_W / 2 - 0.065), ay, WHEEL_R), 0.05, 0.05, steel, segments=16)
    build_fenders(ay)


TIRE_R = 0.39                               # skutečný poloměr pneu Destination Farm 280/70 R15 ve hře (physics 0,385 + 0,005); střed kola je WHEEL_R + TIRE_Y_OFFSET
FENDER_CLEAR = 0.04                         # vůle mezi pneu a plechem blatníku (zdvih odpružení TIRE_SUSP_TRAVEL 0,05)
FENDER_SHEET = 0.008
FENDER_OVER = 0.03                          # blatník přesahuje pneu do stran
FENDER_ARC = (-8.0, 188.0)                  # úhly (od směru dozadu, přes vrch) krytého oblouku
FENDER_Z = WHEEL_R + TIRE_Y_OFFSET          # střed oblouku = osa kola ve hře
FENDER_R_OUT = TIRE_R + FENDER_CLEAR + FENDER_SHEET
MUDFLAP_W, MUDFLAP_H = 0.30, 0.22


def _arc_prism(name, y_c, z_c, r0, r1, a0, a1, x0, x1, mat, steps=32):
    """Výseč mezikruží r0..r1 v rovině YZ (úhel od osy +Y přes +Z), vytažená po X od x0 do x1: plech blatníku."""
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


def build_fenders(ay):
    """Blatníky jako u Utili Trailer 2: kryt kola s přesahem, vnitřní stěna těsně u lemu paluby (držáky k lemu), vnější lem a zástěra
    za kolem. Stojí pevně na rámu (kolo se pod nimi odpruží o suspTravel)."""
    r_out = FENDER_R_OUT
    r_in = r_out - FENDER_SHEET
    rail_x = BASE_W / 2
    a0, a1 = FENDER_ARC
    for side, sx in (("L", 1), ("R", -1)):
        xw = sx * TRACK_X
        x_rail = sx * (rail_x + 0.005)
        x_edge = xw + sx * (WHEEL_W / 2 + FENDER_OVER)
        # plech končí o 4 mm uvnitř stěny a lemu, ať se jejich plochy nekryjí (z-fighting); stěna a lem jsou o 2 mm pod vnějším povrchem
        xa, xb = sorted((x_rail + sx * 0.004, x_edge - sx * 0.004))
        mat = "SDT_PaintDark"
        _arc_prism(f"Fender_{side}", ay, FENDER_Z, r_in, r_out, a0, a1, xa, xb, mat)
        wall_x = sorted((x_rail, x_rail + sx * FENDER_SHEET))
        _arc_prism(f"FenderInner_{side}", ay, FENDER_Z, 0.22, r_out - 0.002, a0 + 0.5, a1 - 0.5, *wall_x, mat)
        lip_x = sorted((x_edge, x_edge - sx * FENDER_SHEET))
        _arc_prism(f"FenderLip_{side}", ay, FENDER_Z, r_out - 0.05, r_out - 0.002, a0 + 0.5, a1 - 0.5, *lip_x, mat)
        for e, ang in (("F", 165.0), ("R", 15.0)):
            a = math.radians(ang)
            yb, zb = ay + (r_out - 0.02) * math.cos(a), FENDER_Z + (r_out - 0.02) * math.sin(a)
            box(f"FenderBracket_{side}{e}", min(sx * rail_x, sx * (rail_x + 0.01)), max(sx * rail_x, sx * (rail_x + 0.01)),
                yb - 0.03, yb + 0.03, zb - 0.05, zb + 0.01, "SDT_Frame")
        yf = ay + WHEEL_R + 0.045
        zf = WHEEL_R * 0.55 + MUDFLAP_H
        box(f"MudflapBar_{side}", xw - MUDFLAP_W / 2 - 0.01, xw + MUDFLAP_W / 2 + 0.01, yf - 0.012, yf + 0.012, zf - 0.015, zf + 0.012,
            "SDT_Frame")
        box(f"Mudflap_{side}", xw - MUDFLAP_W / 2, xw + MUDFLAP_W / 2, yf - 0.006, yf + 0.006, zf - 0.015 - MUDFLAP_H, zf - 0.015,
            "SDT_Rubber")
        box(f"MudflapWeight_{side}", xw - MUDFLAP_W / 2, xw + MUDFLAP_W / 2, yf - 0.011, yf + 0.011, zf - 0.015 - MUDFLAP_H,
            zf - 0.015 - MUDFLAP_H + 0.03, "SDT_Rubber")


def hose_lay_points():
    """Start, Lay1..Lay8 a směr, kterým hadice vchází do přívodu koncovky. Mini má všech osm bodů Lay jako tvar klidové hadice
    (Lay1-3 pevný úsek, Lay4-8 volná část); nájezd (HOSE_LEAD) a přívod koncovky přidává hose_rest_path."""
    end, din = hose_inlet()
    return Vector(HOSE_START), [Vector(p) for p in HOSE_LAY], din


def hose_rest_path():
    """Klidová křivka hadice stejně jako SprayDroneService.getRestLine v Lua: Catmull-Rom přes fillHoseStart a body Lay (koncové body
    blízko koncovky se vynechají), pak začátek rovného nájezdu a konec hadice v přívodu koncovky; v lokálním minimu výšky je tečna
    vodorovná, poslední dva body mají tečnu ve směru přívodu."""
    start, lay, din = hose_lay_points()
    end, _ = hose_inlet()
    lead_start = end - din * HOSE_LEAD
    tip = nozzle_park_matrix().translation
    lay = list(lay)
    while lay and ((lay[-1] - tip).length < 0.3 or (lay[-1] - lead_start).length < 0.12):
        lay.pop()
    pts = [start] + lay + [lead_start, end]
    n = len(pts)
    tangents = {n - 2: din, n - 1: din}
    for i in range(1, n - 2):
        if pts[i].z <= pts[i - 1].z + 1e-4 and pts[i].z <= pts[i + 1].z + 1e-4:
            t = (pts[i + 1] - pts[i - 1]) / 2
            tangents[i] = Vector((t.x, t.y, 0.0))
    return P.hermite_path(pts, tangents=tangents, samples=16)


def _hose_point_at_x(x):
    """Bod klidové hadice (x, y, z) nejblíž dané souřadnici x na úseku od navíječe ke středu vleku."""
    path = [Vector(p) for p in hose_rest_path()]
    i = min(range(len(path)), key=lambda k: abs(path[k].x - x) if path[k].y < 0.0 else 1e9)
    return path[i].x, path[i].y, path[i].z


def _hose_x_at_y(y):
    """Souřadnice x klidové hadice tam, kde protíná rovinu y (přední stěna bedny)."""
    path = [Vector(p) for p in hose_rest_path()]
    return min(path, key=lambda p: abs(p.y - y)).x


def mount_hose_on_tray():
    """Dřív přepojovalo konec hadice na vysouvací desku (padTray); ta od bedny (Pavel 2026-10-09) neexistuje - dron
    stojí rovnou na pevné palubě, takže hadici netřeba nikam přepojovat. Funkce zůstává (volá ji build()) jako
    no-op, dokud se trasa k bedně doladí v Lua - viz TODO u HOSE_LAY."""
    pass


# ------------------------------------------------------------------------------------------------------ výbava celkem
def build_equipment():
    z = DECK_TOP
    build_pad_tank()
    build_pad_crate()
    ix, iy = INDUCTION_XY
    T.build_induction_tank("Tank_Induction", ix, iy, z, T.INDUCTION_R, stand_h=T.INDUCTION_STAND_H,
                           cone_h=T.INDUCTION_CONE_H, body_h=T.INDUCTION_BODY_H)
    gen = build_rotated_generator(z)
    neck = P.empty("dieselNeckNode", gen["cap"])
    neck.empty_display_size = 0.10
    px, py = PUMP_XY
    T.build_pump("Pump", px, py, z)
    build_mini_plumbing(z)
    build_mini_toolbox()
    # druhá bedna u levého lemu: staví se stejným kódem jako první, jenže jeho závěs je na hraně x1 (u levého lemu), ne u nádrže -
    # proto se po postavení celá (i s pivotem víka a aktivačním uzlem) otočí o 180° kolem svého středu, závěs pak leží u nádrže
    # a kladné natočení víka ho odklopí stejným směrem (k nádrži) jako u první bedny.
    global BOX_X
    _orig_box_x = BOX_X
    BOX_X = BOX2_X
    _before_box2 = {o.name for o in bpy.data.objects}
    build_mini_toolbox(suffix="2", canister_offset=BOX_SLOTS)
    BOX_X = _orig_box_x
    _b2x0, _b2x1 = BOX2_X
    _b2y0, _b2y1 = BOX_Y
    _box2_c = Vector(((_b2x0 + _b2x1) / 2, (_b2y0 + _b2y1) / 2, 0))
    _transform_new(_before_box2, Matrix.Translation(_box2_c) @ Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Translation(-_box2_c))
    # znak designu na vnějším boku obou beden v mezeře mezi prostředními žebry (před blatníkem, pod víkem)
    ym = (BOX_Y[0] + BOX_Y[1]) / 2
    for place, sx in (("toolbox", -1), ("toolbox2", 1)):
        brand_mark(place, (sx * BOX2_X[1], ym, DECK_TOP + 0.22), (sx, 0, 0), (0, 0, 1), 0.15, bpy.data.objects[ROOT_NAME])


def equipment_collisions():
    z = DECK_TOP
    gx, gy = GEN_POS
    px, py = PUMP_XY
    ix, iy = INDUCTION_XY
    tee = T.pump_ports(px, py, z)["tee"]
    bx0, bx1 = BOX_X
    by0, by1 = BOX_Y
    b2x0, b2x1 = BOX2_X
    g0x0, g0x1 = BAY2_GAP_X
    g0y0, g0y1 = BAY2_GAP_Y
    return {
        "colToolbox": (bx0 - 0.008, bx1 + 0.008, by0 - 0.016, by1 + 0.010, z, z + BOX_H + 0.02),
        "colToolbox2": (b2x0 - 0.008, b2x1 + 0.008, by0 - 0.016, by1 + 0.010, z, z + BOX_H + 0.02),
        "colBatteryBay": (g0x0 - 0.01, g0x1 + 0.01, g0y0 - 0.01, g0y1 + 0.01, z, z + 0.42),
        "colGenerator": (gx - G.FY - 0.023, gx + G.FY + 0.023, gy - G.FX - 0.023, gy + G.FX + 0.023, z, z + 0.84),
        "colHoseReel": (REEL_X - REEL_R_FLANGE, REEL_X + REEL_R_FLANGE, SWIVEL_Y - 0.0175, REEL_Y + 0.082, z, REEL_Z + REEL_R_FLANGE),
        "colInductionTank": (ix - T.INDUCTION_R - 0.015, ix + T.INDUCTION_R + 0.015, iy - T.INDUCTION_R - 0.015,
                             iy + T.INDUCTION_R + 0.015, z,
                             z + T.INDUCTION_STAND_H + T.INDUCTION_CONE_H + T.INDUCTION_BODY_H),
        "colPump": (px - 0.262, px + 0.316, py - 0.185, py + 0.185, z, z + T.PUMP_AXIS_H + 0.25),
        "colMixer": (tee.x - 0.150, tee.x + 0.150, tee.y - 0.100, tee.y + 0.250, z, tee.z + 0.47),
    }


def build_i3d_structure(vis):
    """Uspořádání pro FS25 jako u velkého vleku: kolizní komponenta jako kořen, kolize výbavy, plnicí uzly, kola, světla."""
    rail_z0 = DECK_TOP - RAIL_H
    # vlastní tvar kořene je jen drobná krychle: skutečný box rámu je dětský tvar colChassis. Po zmrazení rozloženého vleku (kinematické těleso)
    # se kolize dětských tvarů vrací skriptem o těžiště zpět (SprayDroneStation.updateFreeze), kořenový tvar by zůstal posunutý
    comp = _shape_box(COMPONENT_NAME, None, -0.02, 0.02, 0.0, 0.04, DECK_TOP - 0.10, DECK_TOP - 0.06, COL_VEHICLE, dynamic=True,
                      compound=True)
    vis.parent = comp
    vis.matrix_parent_inverse = Matrix.Identity(4)
    cols = _group("collisions", comp)
    child = dict(compoundChild=True, density=0.001)
    _shape_box("colChassis", cols, -BASE_W / 2, BASE_W / 2, BASE_Y0, BASE_Y1, rail_z0, DECK_TOP, COL_VEHICLE, **child)
    _shape_box("colTank", cols, -PAD_W / 2, PAD_W / 2, PAD_Y0, PAD_Y0 + PAD_L, DECK_TOP, TANK_TOP, COL_VEHICLE, **child)
    for name, box_ in equipment_collisions().items():
        _shape_box(name, cols, *box_, COL_VEHICLE, **child)
    _shape_box("colDrawbar", cols, -0.12, 0.12, COUPLER_Y + 0.20, BASE_Y0, COUPLER_Z - 0.05, COUPLER_Z + 0.08,
               COL_VEHICLE, **child)
    # blatníky (Pavel 2026-10-13: kolize všude): deska nad kolem
    for side, sx in (("L", 1), ("R", -1)):
        fa, fb = sorted((sx * (BASE_W / 2), sx * (TRACK_X + WHEEL_W / 2 + FENDER_OVER)))
        _shape_box(f"colFender{side}", cols, fa, fb, AXLE_Y[0] - FENDER_R_OUT * 0.6, AXLE_Y[-1] + FENDER_R_OUT * 0.6,
                   FENDER_Z + FENDER_R_OUT * 0.55, FENDER_Z + FENDER_R_OUT, COL_VEHICLE, **child)

    wheels = _group("wheels", vis)
    bpy.context.view_layer.update()
    for ay, pos in zip(AXLE_Y, ("Front", "Back")):
        for sx, side in ((1, "Left"), (-1, "Right")):
            wheel = _group(f"wheel{pos}{side}", wheels, (sx * TRACK_X, ay, WHEEL_R))
            # náboj a brzdový buben jedou s odpruženým kolem (hra ho posouvá po zdvihu), nezůstanou viset na rámu
            for part in (f"BrakeDrum_{side[0]}", f"Hub_{side[0]}"):
                _set_parent(bpy.data.objects[part], wheel, bpy.data.objects[part].matrix_world.copy())

    fill = _group("fill", vis)
    _shape_box("fillTrigger", fill, -BASE_W / 2 - 0.3, BASE_W / 2 + 0.3, BASE_Y0 - 0.3, BASE_Y1 + 0.3, 0.0,
               DECK_TOP + 1.3, COL_TRIGGER, kinematic=True, compound=True, trigger=True)
    _shape_box("exactFillRootNode", fill, -PAD_W / 2, PAD_W / 2, PAD_Y0, PAD_Y0 + PAD_L, DECK_TOP + PAD_GAP, TANK_TOP,
               COL_FILL_ROOT, kinematic=True, compound=True)
    _shape_box("concentrateFillRootNode", fill, *T.induction_fill_box(*INDUCTION_XY, DECK_TOP), COL_FILL_ROOT,
               kinematic=True, compound=True)
    gx, gy = GEN_POS
    _shape_box("dieselFillRootNode", fill, gx - G.FY - 0.02, gx + G.FY + 0.02, gy - G.FX - 0.02, gy + G.FX + 0.02,
               DECK_TOP + 0.05, DECK_TOP + 0.80, COL_FILL_ROOT, kinematic=True, compound=True)

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
    _group("occlusionAreaStart", occ, (0.85, BASE_Y0, 0))
    _group("occlusionAreaWidth", occ, (-0.85, BASE_Y0, 0))
    _group("occlusionAreaHeight", occ, (0.85, BASE_Y1, 0))
    plate = _group("licensePlateBack", vis, (0, BASE_Y1 + 0.001, rail_z0 - 0.07))
    plate.rotation_euler = (0, 0, math.radians(180))
    return comp


def build_decals():
    """Nálepky: výstražné pruhy na zadním nosníku, nápis na bocích lemu."""
    rz0, rh, rw = DECK_TOP - RAIL_H + 0.03, 0.12, 0.40
    sub = (0.0, 0.0, rw / rh / 16.0, 1.0)
    P.decal_quad("Decal_StripeRearL", (0.60, BASE_Y1, rz0), (-1, 0, 0), (0, 0, 1), rw, rh, "stripe", sub)
    P.decal_quad("Decal_StripeRearR", (-0.20, BASE_Y1, rz0), (-1, 0, 0), (0, 0, 1), rw, rh, "stripe", sub)
    P.decal_quad("Decal_StripeFront", (-BASE_W / 2 + 0.2, BASE_Y0, rz0), (1, 0, 0), (0, 0, 1), BASE_W - 0.4, rh, "stripe",
                 (0.0, 0.0, 1.0, 1.0))


# retranslační tyč: jedna, vpravo vně lemu paluby před kolem (dva U-třmeny s deskou na boční liště), čelo vzadu
RELAY_SLOT_MINI = (1, -1.01, -2.50, -1.05, 0.63, False)
RELAY_CLAMPS_MINI = (-2.25, -1.70)
# Displej plánovače (Pavel 2026-10-15): tablet leží naplocho na palubě u pravého lemu hned za navíječem hadice, obrazovkou
# nahoru, delší stranou podél vleku, na nízké patce ze zadní strany - bez stojánku. Uvnitř složené bedny s dronem.
PLANNER_CENTER = (-0.74, 0.27, DECK_TOP + 0.02 + 0.02)     # střed tabletu: patka 2 cm + půl tloušťky


def build_relay_holders():
    i, x, y0, y1, z, front = RELAY_SLOT_MINI
    relay_pole_mockup(i, x, y0, y1, z, front, scale=0.85)
    for n, y in enumerate(RELAY_CLAMPS_MINI):
        relay_clamp(f"RelayClamp_{i}_{n}", x, y, z, -1, -BASE_W / 2, r=0.068, wire=0.006, plate_h=0.12)


def build_planner_tablet():
    """Tablet plánovače ležící na palubě (viz PLANNER_CENTER): plannerDisplay a uzel plannerScreenNode."""
    disp, node, _ = planner_display(PLANNER_CENTER, (0, 0, 1), (1, 0, 0))
    # SprayDroneLink.isAtScreen měří vodorovnou vzdálenost v rovině XZ uzlu: i3d +Z (= -Y uzlu v Blenderu) musí mířit
    # vodorovně ven k pravému boku (-X) a i3d +Y (= +Z v Blenderu) nahoru, i když obrazovka sama míří nahoru
    m = Matrix(((0, -1, 0), (1, 0, 0), (0, 0, 1))).transposed().to_4x4()
    m.translation = node.matrix_world.translation
    node.matrix_world = m
    return node


def set_ladder(t):
    """Žebřík tu není; jen kvůli rozhraní exportu."""
    return None


def build():
    coll, vis = P.begin(COLLECTION_NAME, ROOT_NAME)
    build_chassis()
    build_drawbar()
    build_equipment()
    build_i3d_structure(vis)
    move_to_preview(("Wheel_", "Rim_"))
    build_drones()
    for prefix in DRONE_VARIANTS.values():
        place_drone(prefix)
        build_drone_leds(prefix)
        build_drone_service_parts_mini(prefix)
        build_drone_decals(prefix)
        mount_drone_on_tray(prefix)
    build_batteries()
    _before_bay = {o.name for o in bpy.data.objects}
    build_bay()
    attach_batteries()
    build_bay_lid()
    # šachta baterií za centrálu (Pavel 2026-10-07, uvolňuje původní místo pro druhou bednu): přirozená orientace šachty
    # je úzká-dlouhá podél Y, cílová mezera za centrálou je široká-mělká -> postavit na původním místě, pak otočit o 90°
    _bx0, _bx1, _by0, _by1, _, _, _ = bay_box()
    _old_c = Vector(((_bx0 + _bx1) / 2, (_by0 + _by1) / 2, 0))
    _gx0, _gx1 = BAY2_GAP_X
    _gy0, _gy1 = BAY2_GAP_Y
    _new_c = Vector(((_gx0 + _gx1) / 2, (_gy0 + _gy1) / 2, 0))
    _transform_new(_before_bay, Matrix.Translation(_new_c) @ BAY_ROTATE_MATRIX @ Matrix.Translation(-_old_c))
    build_charger_cable()
    build_fill_hose()
    mount_hose_on_tray()
    build_decals()
    build_relay_holders()
    build_planner_tablet()
    bpy.context.view_layer.update()
    build_dirt_uvs()
    print(f"{COLLECTION_NAME}: {len(coll.objects)} objektů")


if __name__ == "__main__":
    build()
