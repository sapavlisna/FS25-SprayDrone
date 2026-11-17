"""Malý servisní vlek: všechno na jedné palubě, dron S stojí na přistávací desce nad hranatou nádrží (450 l).

Skládá se z velkého skriptu build_trailer_car.py: ten se spustí do stejného jmenného prostoru, přepíšou se rozměry a
funkce nástavby, podvozek, oj, dron (S), úchyty lyžin, rozkládání dronu a mapy špíny zůstanou stejné. Uspořádání shora
(+X vlevo, -Y dopředu k oji):

    vpředu         elektrocentrála vlevo (otočená: panel vpřed, hrdlo nádrže vlevo vpředu mimo desku), vpravo indukční
                   nádrž; za nimi čerpadlo a mixér
    uprostřed      hranatá nádrž 0,6 x 0,95 x 0,93 m, po bocích vlevo šachta na 3 baterie a vpravo bedna na 4 kanystry
                   (víka se otevírají dovnitř pod desku)
    nahoře         přistávací deska 1,6 x 2,2 m na nosnících, sahá od zadní hrany přes nádrž a šachty až nad čerpadlo a
                   mixér (přední část je převis na šikmých vzpěrách); složený dron na ní stojí celý

Spuštění v Blenderu:
    p = r"...\\build_trailer_mini.py"; exec(open(p, encoding="utf-8").read(), {"__file__": p, "__name__": "__main__"})
Bez okna (přestavba + uložení do spraydrone_trailer_mini.blend): viz headless_mini.py.
"""

import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_big = os.path.join(_HERE, "build_trailer_car.py")
exec(compile(open(_big, encoding="utf-8").read(), _big, "exec"), globals())

# ---------------------------------------------------------------------------------------------------------- konstanty
V = T.V
L = BT.L

COLLECTION_NAME = "SprayDroneTrailerMini"
PREVIEW_COLLECTION = "SprayDroneTrailerMini_Preview"
COMPONENT_NAME = "sprayDroneTrailerMini_main_component1"
ROOT_NAME = "sprayDroneTrailerMini_vis"

BASE_LEN = 2.85                      # za nádrží je místo, aby se složený dron (ramena dozadu) vešel celý nad palubu
BASE_W = 1.86
BASE_Y0 = -2.60                      # spojka zůstává jako u velkého vleku (COUPLER_Y -3,55), oj je tak jen 1 m
_Y = BASE_Y0 + 2.10                  # posun polohy po ose Y oproti návrhu s palubou od -2,10
BASE_Y1 = BASE_Y0 + BASE_LEN
TRACK_X = 0.72
AXLE_Y = [-0.55 + _Y]                # jedna náprava pod nádrží, těžiště mírně před ní (kladná váha na oji)

DRONE_VARIANTS = {"S": "Drone_S_"}
DRONE_PREFIX = DRONE_VARIANTS["S"]
DRONE_HIDDEN = ()
BATTERY_COUNT = 3

PAD_W, PAD_H, PAD_L = 0.60, 0.93, 0.95     # hranatá nádrž (~450 l), pod přistávací deskou; deska sahá přes mixér (0,89 m)
PAD_GAP = 0.04
PAD_Y0 = -0.87 + _Y                         # přední stěna; výpust v kontraktu je o 6 cm za ní
PAD_LITERS = 450
TANK_TOP = DECK_TOP + PAD_GAP + PAD_H
PLATE_BEAM_H, PLATE_T = 0.08, 0.04          # nosníky pod deskou dosedají na nádrž a boční sloupky; tloušťka desky
PLATE_Y0 = -2.02                            # přední hrana desky: o 5 cm před mixérem (y -1,97), takže kryje čerpadlo i mixér
PLATE_Y1 = BASE_Y1 - 0.07
PLATE_W, PLATE_L = 1.60, PLATE_Y1 - PLATE_Y0   # přistávací deska: dron složený (1,28 x 1,38 m) se vejde celý
TOP_SURF = TANK_TOP + PLATE_BEAM_H + PLATE_T    # horní plocha desky = podložka dronu
DRONE_Y = PAD_Y0 + PAD_L / 2                # nad středem nádrže; ramena se skládají dozadu (+1,0 m), vejdou se na desku
CLAMP_Y = (DRONE_Y - 0.075, DRONE_Y + 0.075)   # úchyty lyžin dronu (velký vlek má dron v y = 0)
CAMERA_TARGET = (0.0, DRONE_Y, TOP_SURF + 1.0)
EXIT_POINT = (BASE_W / 2 + 1.0, BASE_Y1 - 0.6, 0.0)

GEN_POS = (0.50, -2.15)                     # centrála vpředu vlevo, otočená o -90°: panel vpřed, hrdlo nádrže vlevo vpředu
GEN_ROT = -math.pi / 2
GEN_SOCKET_LOCAL = (GEN_POS[0] + 0.33, GEN_POS[1] - 0.10, 1.15)     # zásuvka v neotočeném stavu (tak ji staví sdt_generator)
GEN_SOCKET = (GEN_POS[0] - 0.10, GEN_POS[1] - 0.33, 1.15)           # po otočení: na čelním panelu
CLUSTER_SHIFT = (-0.03, -0.57 + _Y)            # čerpadlo, indukční nádrž a výpust jako u velkého vleku, posunuté sem
PUMP_XY = (-0.55 + CLUSTER_SHIFT[0], -0.55 + CLUSTER_SHIFT[1])
INDUCTION_XY = (-0.55 + CLUSTER_SHIFT[0], -1.25 + CLUSTER_SHIFT[1])
MAIN_DRAIN = Vector((0.125 + CLUSTER_SHIFT[0], -0.239 + CLUSTER_SHIFT[1], 1.0025))

STRIP_X = (0.40, 0.72)                      # pásy po bocích nádrže pod deskou (vlevo baterie, vpravo kanystry)
BAY_Y = (-0.80 + _Y, -0.04 + _Y)
BAY_CELLS = tuple(c + _Y for c in (-0.705, -0.515, -0.325, -0.135))   # tři šachty baterií a ovládací panel
BAY_SHAFT = (0.21, 0.13)
BAY_WALL = 0.03
BAY_FEET = 0.015
BAY_DOCK = 0.035
BAY_LID_CLEAR = 0.085
BAY_LID_T = 0.025
BAY_LID_OPEN_DEG = 100
BAY_LID_BASIS = Euler((0, 0, -math.pi / 2)).to_matrix().to_4x4()     # závěs u nádrže: osa závěsu = Y vleku, víko míří ven
LID_TIME = (1.8, 3.0)
CABLE_TIME = (0.0, 0.05)
BOX_X = (-0.72, -0.40)
BOX_Y = (-0.83 + _Y, -0.03 + _Y)
BOX_H = 0.46
BOX_SLOTS = 4
BOX_PITCH = 0.20
CAN_W, CAN_D, CAN_H = T.CANISTER

LIGHT_NODES = [
    ("rearLight52_left", (0.78, BASE_Y1 + 0.005, DECK_TOP - RAIL_H + 0.08), (-90, 0, 180)),
    ("rearLight52_right", (-0.78, BASE_Y1 + 0.005, DECK_TOP - RAIL_H + 0.08), (-90, 0, 180)),
    ("plateNumberLight03", (0.0, BASE_Y1 + 0.005, DECK_TOP - RAIL_H - 0.005), (-90, 0, -90)),
    ("sideMarker05_left", (BASE_W / 2 + 0.003, BASE_Y1 - 0.12, DECK_TOP - RAIL_H + 0.09), (0, 0, -90)),
    ("sideMarker05_right", (-BASE_W / 2 - 0.003, BASE_Y1 - 0.12, DECK_TOP - RAIL_H + 0.09), (0, 0, 90)),
]

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
        self.wv = 0.40


def pad_label_geometry(t):
    wv = t.wv
    hv = wv / 1.6
    wp = 0.15
    hp = wp / 1.6
    return {"vol": (t.mid, 0.07, wv, hv), "plate": (t.mid, 0.07 - hv / 2 - 0.025 - hp / 2, wp, hp)}


def build_pad_tank():
    """Hranatá PE nádrž 450 l: zaoblený kvádr, kruhové plnicí hrdlo na zadní stěně, výpust vpředu jako u velkého vleku."""
    z = DECK_TOP
    t = PadTank(z)
    name = "Tank_Main"
    shell, fit, lid, frm = (BT.Mesh(n) for n in (name, f"{name}_Fittings", f"{name}_Lid", f"{name}_Frame"))
    hw = t.hw
    BT._rounded_box(shell, -hw, hw, t.y0, t.y0 + t.Ln, t.zb, t.zt, BT.PE, BT.BOX_EDGE_R)
    ya, yb = t.y0 + 0.08, t.y0 + t.Ln - 0.08
    for dz in (-0.27, 0.27):
        for s in (-1, 1):
            shell.box(s * (hw - 0.002), s * (hw + 0.007), ya, yb, t.zc + dz - 0.014, t.zc + dz + 0.014, BT.PE, bevel=0.004)
    lab = pad_label_geometry(t)
    u, dz, w, h = lab["vol"]
    for side in (1, -1):
        BT._box_panel(t, shell, side, t.y0 + u, t.zc + dz, w + 0.03, h + 0.03)
    u, dz, w, h = lab["plate"]
    BT._box_panel(t, shell, 1, t.y0 + u, t.zc + dz, w + 0.03, h + 0.03, bar=0.007, rise=0.003)
    BT._box_panel(t, shell, 1, t.y0 + u, t.zc + dz, w + 0.012, h + 0.012, solid=True, rise=0.001)

    # plnicí hrdlo uprostřed zadní stěny (nahoře leží přistávací deska)
    hx, hz, yr = 0.0, t.zc - 0.04, t.y0 + t.Ln
    ax = V(0, 1, 0)
    shell.lathe([(0.15, -0.05), (0.15, 0.012), (0.165, 0.014), (0.165, 0.026), (0.14, 0.030), (0.0, 0.030)],
                V(hx, yr, hz), ax, BT.PE, seg=40, hard=(1, 2, 3, 4), ref=V(0, 0, 1))
    lid.lathe([(0, 0), (0.15, 0), (0.15, 0.012), (0.138, 0.022), (0.10, 0.028), (0, 0.030)],
              V(hx, yr + 0.030, hz), ax, BT.BLACK, seg=40, hard=(1, 2, 3), ref=V(0, 0, 1))
    for k in range(6):
        a = BT.TAU * (k + 0.5) / 6
        fit.hex(V(hx + 0.118 * math.cos(a), yr + 0.068, hz + 0.118 * math.sin(a)), ax, 0.011, 0.012, BT.STEEL)
    fit.box(hx - 0.07, hx + 0.07, yr + 0.058, yr + 0.072, hz - 0.012, hz + 0.012, BT.BLACK, bevel=0.004)
    fit.torus(V(hx, yr + 0.031, hz), ax, 0.138, 0.004, BT.RUBBER, seg=40, rseg=4)
    BT._vent_at(fit, V(0.22, t.y0 + t.Ln, t.zt - 0.10), V(0, 1, 0), 0.7)

    BT._outlet(t, fit)
    BT._rear_drain_at(fit, V(0.24, t.y0 + t.Ln, t.zb + 0.12), V(0, 1, 0), V(0, 0, -1), 0.45)
    BT._box_frame(t, frm, eyes=False)
    meshes = [m.finish() for m in (shell, fit, lid, frm)]
    bpy.context.view_layer.update()

    decals = []

    def put(nm, side, uu, dz_, w_, h_, region, sub_=None, offset=0.0022):
        uax, vax = V(0, side, 0), V(0, 0, 1)
        c = V(side * t.hw, t.y0 + uu, t.zc + dz_)
        decals.append(P.decal_quad(nm, c - uax * w_ / 2 - vax * h_ / 2, uax, vax, w_, h_, region, sub=sub_, offset=offset))

    u, dz, w, h = lab["vol"]
    put(f"{name}_VolL", 1, u, dz, w, h, f"tankVol{PAD_LITERS}")
    put(f"{name}_VolR", -1, u, dz, w, h, f"tankVol{PAD_LITERS}")
    u, dz, w, h = lab["plate"]
    put(f"{name}_Plate", 1, u, dz, w, h, f"tankPlate{PAD_LITERS}", offset=0.0025)
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
    fit.cyl(o + V(0, 0, 0.134), o + V(0, 0, 0.190), 0.030, "SDT_Steel", seg=16)
    fit.cyl(o + V(0, 0, 0.190), o + V(0, 0, 0.215), 0.036, "SDT_Plastic", seg=16)
    fit.torus(o + V(0, 0, 0.165), V(0, 0, 1), 0.034, 0.004, "SDT_Steel", seg=16, rseg=4)

    drain = MAIN_DRAIN
    a = drain + V(0, -T.MAIN_DRAIN_HOSE, 0)
    fit.clamp(drain + V(0, -(T.MAIN_DRAIN_HOSE - 0.014), 0), V(0, 1, 0), 0.0255)
    b = ports["water_end"]
    P.sweep("Pump_Suction", P.hermite_path([a, b], tangents={0: (0, -1, 0), 1: (-1, 0, 0)}, samples=20), 0.025,
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
    """Šachta na tři baterie S (stojí svisle konektorem dolů, nad hranu čouhá horní čelo s madlem) a ovládací panel,
    tmavý korpus na patkách u levého okraje paluby. batterySlotDeck1..3 jsou její děti."""
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
        lx0, lx1 = x1 - w + 0.008, x1 - 0.008
        for n in range(4):
            ly = cy - 0.036 + n * 0.024
            led = box(f"Charger_Led_{k}_{n}", lx0, lx1, ly - 0.008, ly + 0.008, top + rim, top + rim + 0.003, "SDT_Decal")
            P.planar_uv(led, (lx0, ly - 0.008, 0), (1, 0, 0), (0, 1, 0), lx1 - lx0, 0.016, "led")
            parts.append(led)
        _group(f"batterySlotDeck{k}", bay).matrix_world = (
            Matrix.Translation((cx, cy + P.BATTERY_SIZE[2] / 2, dock + 0.016 + P.BATTERY_SIZE[0] / 2)) @ BATTERY_STAND)
    cy = BAY_CELLS[-1]
    parts.append(box("Charger_ConsoleFill", x0 + w, x1 - w, cy - sy / 2, cy + sy / 2, dock, top, "SDT_ChargerGrey"))
    tilt = Matrix.Translation((cx, cy, top + 0.025)) @ Matrix.Rotation(math.radians(-28), 4, "X")
    console = [
        box("Charger_Console", -0.11, 0.11, -0.055, 0.055, -0.07, 0.02, "SDT_ChargerGrey"),
        box("Charger_Screen", -0.08, 0.05, -0.04, 0.04, 0.02, 0.023, "SDT_Decal"),
        box("Charger_Power", 0.07, 0.095, -0.03, -0.01, 0.02, 0.026, "SDT_LedGreen"),
        box("Charger_ButtonA", 0.07, 0.095, 0.0, 0.02, 0.02, 0.028, "SDT_TankBlack"),
    ]
    for o in console:
        o.matrix_world = tilt @ o.matrix_world
    rot = tilt.to_3x3()
    P.planar_uv(console[1], tilt @ Vector((0.05, 0.04, 0.023)), rot @ Vector((-1, 0, 0)), rot @ Vector((0, -1, 0)),
                0.13, 0.08, "chargerScreen")
    parts += console
    zs = [dock + 0.05 + 0.032 * n for n in range(int((top - dock - 0.12) / 0.032) + 1)]
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


def charger_cable_points():
    x0, x1, y0, y1, zw = bay_lid_geometry()
    sy, sz = y0 + 0.10, DECK_TOP + 0.13
    gx, gy, gz = GEN_SOCKET
    lip = BASE_W / 2
    # zásuvka centrály je na čelním panelu (míří -Y): kabel jde dopředu a dolů, vlevo ven přes lem a po vnější straně k šachtě
    return [(gx, gy - 0.045, gz), (gx, gy - 0.075, gz - 0.04), (gx + 0.02, gy - 0.12, gz - 0.12),
            (gx + 0.12, gy - 0.13, 0.96), (gx + 0.30, gy - 0.12, 0.84), (lip - 0.05, gy - 0.10, 0.76),
            (lip + 0.022, gy + 0.10, DECK_TOP + 0.02), (lip + 0.024, (sy + gy) / 2, DECK_TOP + 0.04),
            (lip + 0.020, sy - 0.12, DECK_TOP + 0.02), (x1 + 0.07, sy - 0.02, sz - 0.07),
            (x1 + 0.058, sy - 0.003, sz - 0.04), (x1 + 0.05, sy, sz)]


def build_charger_cable():
    """Kabel generátor -> zásuvka na šachtě baterií po vnější straně levého lemu; plug na obou koncích."""
    path = P.hermite_path(charger_cable_points(), samples=12)
    cable = P.sweep("chargerCable", path, CABLE_R, "SDT_HoseBlack", segments=10)
    x0, x1, y0, y1, zw = bay_lid_geometry()
    sy, sz = y0 + 0.10, DECK_TOP + 0.13
    gx, gy, gz = GEN_SOCKET
    plugs = [
        tube("Charger_Plug", (x1 + 0.02, sy, sz), (x1 + 0.055, sy, sz), 0.018, "SDT_Rubber", segments=12, radius_end=0.012),
        tube("Gen_0_ChargePlug", (gx, gy - 0.015, gz), (gx, gy - 0.05, gz), 0.018, "SDT_Rubber", segments=12,
             radius_end=0.012),
    ]
    for o in plugs:
        _set_parent(o, cable, o.matrix_world.copy())
    return cable, P.path_length(path)


# ------------------------------------------------------------------------------------------------ bedna na kanystry
def build_mini_toolbox():
    """Bedna na 4 kanystry 20 l vpravo od nádrže: tmavý korpus se čtyřmi přihrádkami v řadě, víko na předním závěsu
    (toolboxLid, otevírá se kladným natočením kolem osy X), uzly toolboxCanister1..4 a toolboxActivateNode."""
    vis = bpy.data.objects[ROOT_NAME]
    x0, x1 = BOX_X
    y0, y1 = BOX_Y
    z0 = DECK_TOP
    foot = 0.024
    zb = z0 + foot
    zs = z0 + BOX_H - 0.045
    t = 0.010
    dark = "SDT_PaintDark"
    body = T.Mesh("Toolbox")
    inner = T.Mesh("Toolbox_Inner")
    hw = T.Mesh("Toolbox_Hardware")
    lid = T.Mesh("Toolbox_Lid")
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
    pz0, pz1 = zb + 0.05, zs - 0.05
    body.box(x0 + 0.04, x1 - 0.04, y1, y1 + 0.004, pz0, pz1, dark, bevel=0.004)
    body.box(x0 + 0.04, x1 - 0.04, y0 - 0.004, y0, pz0, pz1, dark, bevel=0.004)
    body.box(x0 - 0.004, x0, y0 + 0.07, y1 - 0.07, pz0, pz1, dark, bevel=0.004)

    # víko: miska s lemem dolů, závěs na vnitřním okraji (u nádrže), otevírá se dovnitř pod desku; základní natočení Rz(+90°)
    ym = (y0 + y1) / 2
    hx = x1 + 0.010
    zl = zs + 0.004
    lid.box(x0 - 0.010, x1 + 0.010, y0 - 0.010, y1 + 0.010, zl, zl + 0.030, dark, bevel=0.004)
    lid.box(x0 - 0.010, x1 + 0.010, y0 - 0.010, y0, zl - 0.040, zl, dark)
    lid.box(x0 - 0.010, x1 + 0.010, y1, y1 + 0.010, zl - 0.040, zl, dark)
    lid.box(x0 - 0.010, x0, y0, y1, zl - 0.040, zl, dark)
    lid.box(x0 + 0.030, x0 + 0.055, y0 + 0.05, y1 - 0.05, zl + 0.030, zl + 0.032, "SDT_GenOrange")
    for yy in (ym - 0.20, ym + 0.20):
        lid.box(x0 - 0.018, x0 - 0.010, yy - 0.025, yy + 0.025, zl - 0.050, zl + 0.010, "SDT_Steel")
        lid.cyl(V(hx, yy - 0.045, zl + 0.012), V(hx, yy + 0.045, zl + 0.012), 0.011, "SDT_Steel", seg=10)
    lid.cyl(V(x0 - 0.035, ym - 0.07, zl + 0.015), V(x0 - 0.035, ym + 0.07, zl + 0.015), 0.009, "SDT_Steel", seg=10)
    meshes = [m.finish() for m in (body, inner, hw)]
    lid_mesh = lid.finish()
    pivot = _group("toolboxLid", vis, (hx, ym, zl + 0.012))
    pivot.rotation_euler = (0, 0, math.pi / 2)
    bpy.context.view_layer.update()
    _set_parent(lid_mesh, pivot, lid_mesh.matrix_world.copy())
    for m in meshes:
        _set_parent(m, vis, m.matrix_world.copy())
    for k, yy in enumerate(ys, 1):
        can = T.build_canister(f"toolboxCanister{k}", Vector((xm, yy, floor + 0.004)))
        can.matrix_world = Matrix.Translation(Vector((xm, yy, floor + 0.004)))
    act = P.empty("toolboxActivateNode", Vector((xm, (y0 + y1) / 2, zs + 0.20)))
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


# ------------------------------------------------------------------------------------------------ přistávací deska
def build_landing_plate():
    """Přistávací deska 1,6 x 1,5 m nad nádrží a bočními šachtami: pochozí plech na dvou podélných a třech příčných
    nosnících, které dosedají na nádrž, vpředu a vzadu čtyři sloupky na palubě. Nízký lem po obvodu a H mezi lyžinami."""
    z_top = TOP_SURF
    zp0 = z_top - PLATE_T
    zb0 = TANK_TOP
    hx = PLATE_W / 2
    y0, y1 = PLATE_Y0, PLATE_Y1
    frame = "SDT_Frame"
    box("Landing_Plate", -hx, hx, y0, y1, zp0, z_top, "SDT_TopDeck")
    # sloupky jen za čerpadlem (u předního konce stojí centrála, mixér a indukční nádrž), přední část desky vyčnívá volně
    posts_y = (PAD_Y0 - 0.01, y1 - 0.05)
    for side, sx in (("L", 1), ("R", -1)):
        box(f"Landing_Beam_{side}", sx * (hx - 0.07) - 0.035, sx * (hx - 0.07) + 0.035, y0, y1, zb0, zp0, frame)
        box(f"Landing_Lip_{side}", sx * hx - sx * 0.035, sx * hx, y0, y1, z_top, z_top + 0.035, frame)
        for k, py in enumerate(posts_y):
            post_x = sx * (hx - 0.07)
            box(f"Landing_Post_{side}{k}", post_x - 0.035, post_x + 0.035, py - 0.035, py + 0.035, DECK_TOP, zb0, frame)
            box(f"Landing_Foot_{side}{k}", post_x - 0.06, post_x + 0.06, py - 0.06, py + 0.06, DECK_TOP, DECK_TOP + 0.01, frame)
        # šikmá vzpěra pod předním převisem (od sloupku k nosníku)
        post_x = sx * (hx - 0.07)
        tube(f"Landing_Brace_{side}", (post_x, posts_y[0] - 0.035, zb0 - 0.28), (post_x, posts_y[0] - 0.45, zp0), 0.016,
             frame, segments=8)
    for k, py in enumerate((y0 + 0.05, PAD_Y0 - 0.01, PAD_Y0 + PAD_L / 2, y1 - 0.05)):
        box(f"Landing_Cross_{k}", -hx + 0.035, hx - 0.035, py - 0.03, py + 0.03, zb0, zp0, frame)
    box("Landing_Lip_Front", -hx, hx, y0, y0 + 0.035, z_top, z_top + 0.035, frame)
    box("Landing_Lip_Rear", -hx, hx, y1 - 0.035, y1, z_top, z_top + 0.035, frame)
    t0, t1 = z_top, z_top + 0.003
    cy = DRONE_Y
    for nm, xa, xb, ya, yb in (("L", 0.16, 0.20, cy - 0.30, cy + 0.30), ("R", -0.20, -0.16, cy - 0.30, cy + 0.30),
                               ("Bar", -0.16, 0.16, cy - 0.02, cy + 0.02)):
        box(f"Landing_H_{nm}", xa, xb, ya, yb, t0, t1, "SDT_PaintWhite")
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cyy = sx * 0.55, cy + sy * 0.55
            box(f"Landing_Corner_{sx}{sy}a", cx, cx + sx * 0.12, cyy, cyy + sy * 0.025, t0, t1, "SDT_LampAmber")
            box(f"Landing_Corner_{sx}{sy}b", cx, cx + sx * 0.025, cyy, cyy + sy * 0.12, t0, t1, "SDT_LampAmber")


# ------------------------------------------------------------------------------------------------------ výbava celkem
def build_equipment():
    z = DECK_TOP
    build_pad_tank()
    build_landing_plate()
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


def equipment_collisions():
    z = DECK_TOP
    gx, gy = GEN_POS
    px, py = PUMP_XY
    ix, iy = INDUCTION_XY
    tee = T.pump_ports(px, py, z)["tee"]
    bx0, bx1 = BOX_X
    by0, by1 = BOX_Y
    ax0, ax1, ay0, ay1, _, _, _ = bay_box()
    return {
        "colToolbox": (bx0 - 0.008, bx1 + 0.008, by0 - 0.016, by1 + 0.010, z, z + BOX_H + 0.02),
        "colBatteryBay": (ax0 - 0.008, ax1 + 0.008, ay0 - 0.01, ay1 + 0.01, z, z + 0.42),
        "colGenerator": (gx - G.FY - 0.023, gx + G.FY + 0.023, gy - G.FX - 0.023, gy + G.FX + 0.023, z, z + 0.84),
        "colInductionTank": (ix - T.INDUCTION_R - 0.015, ix + T.INDUCTION_R + 0.015, iy - T.INDUCTION_R - 0.015,
                             iy + T.INDUCTION_R + 0.015, z,
                             z + T.INDUCTION_STAND_H + T.INDUCTION_CONE_H + T.INDUCTION_BODY_H),
        "colPump": (px - 0.262, px + 0.316, py - 0.185, py + 0.185, z, z + T.PUMP_AXIS_H + 0.25),
        "colMixer": (tee.x - 0.150, tee.x + 0.150, tee.y - 0.100, tee.y + 0.250, z, tee.z + 0.47),
    }


def build_i3d_structure(vis):
    """Uspořádání pro FS25 jako u velkého vleku: kolizní komponenta jako kořen, kolize výbavy, plnicí uzly, kola, světla."""
    rail_z0 = DECK_TOP - RAIL_H
    comp = _shape_box(COMPONENT_NAME, None, -BASE_W / 2, BASE_W / 2, BASE_Y0, BASE_Y1, rail_z0, DECK_TOP,
                      COL_VEHICLE, dynamic=True, compound=True)
    vis.parent = comp
    vis.matrix_parent_inverse = Matrix.Identity(4)
    cols = _group("collisions", comp)
    child = dict(compoundChild=True, density=0.001)
    _shape_box("colTank", cols, -PAD_W / 2, PAD_W / 2, PAD_Y0, PAD_Y0 + PAD_L, DECK_TOP, TANK_TOP, COL_VEHICLE, **child)
    _shape_box("colLandingPlate", cols, -PLATE_W / 2, PLATE_W / 2, PLATE_Y0, PLATE_Y0 + PLATE_L, TANK_TOP, TOP_SURF,
               COL_VEHICLE, **child)
    for name, box_ in equipment_collisions().items():
        _shape_box(name, cols, *box_, COL_VEHICLE, **child)
    _shape_box("colDrawbar", cols, -0.12, 0.12, COUPLER_Y + 0.20, BASE_Y0, COUPLER_Z - 0.05, COUPLER_Z + 0.08,
               COL_VEHICLE, **child)

    wheels = _group("wheels", vis)
    for ay, pos in zip(AXLE_Y, ("Front", "Back")):
        for sx, side in ((1, "Left"), (-1, "Right")):
            _group(f"wheel{pos}{side}", wheels, (sx * TRACK_X, ay, WHEEL_R))

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
        build_drone_clamps(prefix)
    build_batteries()
    build_bay()
    attach_batteries()
    build_bay_lid()
    build_charger_cable()
    for prefix in DRONE_VARIANTS.values():
        build_drone_service_parts(prefix)
        build_drone_decals(prefix)
    build_decals()
    bpy.context.view_layer.update()
    build_dirt_uvs()
    print(f"{COLLECTION_NAME}: {len(coll.objects)} objektů")


if __name__ == "__main__":
    build()
