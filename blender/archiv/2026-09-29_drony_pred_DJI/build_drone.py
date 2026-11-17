"""Parametricky postaví postřikový dron podle DJI Agras ve třech velikostech (SPECS, viz docs/PLAN-0.9.md).

"M" = T50 (dnešní model): ramena rozložená 1590 x 1900 mm, výška 820 mm, nádrž 40 l, souosé vrtule, 4 trysky.
"S" = T25: jednoduché vrtule 50", nádrž 20 l, 2 trysky pod zadními motory (rozteč 1368 mm).
"L" = T100: souosé vrtule 62", nádrž 100 l, 2 trysky na ramenech postřiku za zadními motory (rozteč 1834 mm).
Rozteč motorů S a L = rozměr rozloženého dronu s vrtulemi minus průměr vrtule.

Vrtule jdou postavit složené (parkování na plošině vleku) i rozložené (let).

Tvarosloví podle referenční fotky: zaoblená skříň trupu s GPS věží, kónická nádrž,
kónická ramena s objímkami, žebrované gondoly, zúžené a zkroucené listy. Díly proto
nevznikají z primitiv, ale loftem mezi profily.

Spustit v Blenderu stejně jako build_trailer.py; helpery a materiály sdílí s ním.
"""

import os
import sys

import bpy
import bmesh
import math
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_trailer as parts

COLLECTION_NAME = "SprayDrone"

# arm_span: rozteč motorů podélně a napříč; body: délka, šířka, výška trupu; blade: délka, tětiva u kořene a u špičky;
# detail: měřítko drobných dílů (věž, gondoly, trubky); skid: y lyžiny, půldélka lyžiny, x nohou;
# fold: azimut předních a zadních ramen po složení; nozzles: ramena s tryskou a jejich vzdálenost od osy napříč
# (None = pod motorem); boom: tryska na rameni postřiku vně motoru
SPECS = {
    "M": dict(arm_span=(1.59, 1.90), arm_z=0.56, body=(0.56, 0.50, 0.17), tank_top=(0.58, 0.48),
              tank_bottom=(0.44, 0.36), tank_h=0.30, blade=(0.68, 0.095, 0.045), motor_r=0.075,
              levels=("Top", "Bottom"), detail=1.0, mast_h=0.15, skid=(0.42, 0.46, 0.30), fold=(160, 176),
              nozzles=(1, 2, 3, 4), nozzle_y=None, boom=False, body_power=4.0),
    "S": dict(arm_span=(1.315, 1.405), arm_z=0.55, body=(0.44, 0.40, 0.15), tank_top=(0.46, 0.38),
              tank_bottom=(0.35, 0.29), tank_h=0.24, blade=(0.635, 0.085, 0.04), motor_r=0.065,
              levels=("Top",), detail=0.85, mast_h=0.155, skid=(0.34, 0.38, 0.24), fold=(157, 176),
              nozzles=(3, 4), nozzle_y=0.684, boom=False, body_power=3.2),
    "L": dict(arm_span=(1.646, 1.65), arm_z=0.67, body=(0.66, 0.56, 0.20), tank_top=(0.74, 0.62),
              tank_bottom=(0.58, 0.48), tank_h=0.38, blade=(0.787, 0.12, 0.055), motor_r=0.10,
              levels=("Top", "Bottom"), detail=1.2, mast_h=0.09, skid=(0.56, 0.58, 0.40), fold=(157, 176),
              nozzles=(3, 4), nozzle_y=0.917, boom=True, body_power=4.5),
}

# výchozí parametry (M) pro volání bez spec
ARM_SPAN_X, ARM_SPAN_Y = SPECS["M"]["arm_span"]
PROPS_FOLDED = True
ARMS_FOLDED = 0.0  # 0 = rozloženo, 1 = složeno podél trupu

RING_SEGMENTS = 20
TUBE_SEGMENTS = 12


def clear_collection():
    if COLLECTION_NAME in bpy.data.collections:
        coll = bpy.data.collections[COLLECTION_NAME]
        for obj in list(coll.objects):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if isinstance(data, bpy.types.Mesh) and data.users == 0:
                bpy.data.meshes.remove(data)
    else:
        coll = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(coll)
    return coll


def superellipse_ring(a, b, z, segments=RING_SEGMENTS, power=4.0):
    """Prstenec mezi kruhem a zaobleným obdélníkem - plášť trupu i nádrže."""
    pts = []
    e = 2.0 / power
    for i in range(segments):
        t = 2 * math.pi * i / segments
        c, s = math.cos(t), math.sin(t)
        pts.append(mathutils.Vector((
            a * math.copysign(abs(c) ** e, c),
            b * math.copysign(abs(s) ** e, s),
            z,
        )))
    return pts


def circle_ring(r, z, segments=RING_SEGMENTS):
    return [
        mathutils.Vector((r * math.cos(2 * math.pi * i / segments), r * math.sin(2 * math.pi * i / segments), z))
        for i in range(segments)
    ]


def _loft_into(bm, rings, cap_start=True, cap_end=True):
    ring_verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(ring_verts, ring_verts[1:]):
        for k in range(n):
            k2 = (k + 1) % n
            bm.faces.new((a[k], a[k2], b[k2], b[k]))
    if cap_start:
        bm.faces.new(list(reversed(ring_verts[0])))
    if cap_end:
        bm.faces.new(ring_verts[-1])


def add_loft(coll, name, rings, mat=None, loc=(0, 0, 0), smooth=True, cap_start=True, cap_end=True):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    _loft_into(bm, rings, cap_start=cap_start, cap_end=cap_end)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    coll.objects.link(obj)
    if mat:
        set_material(obj, mat)
    return obj


def _axis_frame(direction):
    u = mathutils.Vector(direction).normalized()
    up = mathutils.Vector((0, 0, 1))
    if abs(u.dot(up)) > 0.98:
        up = mathutils.Vector((1, 0, 0))
    n1 = u.cross(up).normalized()
    return u, n1, u.cross(n1).normalized()


def tube_rings(p0, p1, radii, segments=TUBE_SEGMENTS):
    """Prstence pro kónickou trubku - `radii` je poloměr v každé stanici podél osy."""
    p0, p1 = mathutils.Vector(p0), mathutils.Vector(p1)
    _, n1, n2 = _axis_frame(p1 - p0)
    rings = []
    for i, r in enumerate(radii):
        t = i / (len(radii) - 1)
        center = p0.lerp(p1, t)
        rings.append([
            center + n1 * (r * math.cos(2 * math.pi * k / segments)) + n2 * (r * math.sin(2 * math.pi * k / segments))
            for k in range(segments)
        ])
    return rings


def set_material(obj, mat_name):
    obj.data.materials.clear()
    obj.data.materials.append(parts.get_material(mat_name))
    return obj


def arm_positions(spec=None):
    span_x, span_y = (spec or SPECS["M"])["arm_span"]
    return [
        (sx * span_x / 2, sy * span_y / 2)
        for sx in (1, -1)
        for sy in (1, -1)
    ]


def add_arm_pivot(coll, name, location):
    """Kloub ramene - v i3d z něj bude animovaný uzel, proto vlastní prázdný objekt."""
    pivot = bpy.data.objects.new(name, None)
    pivot.empty_display_type = 'PLAIN_AXES'
    pivot.empty_display_size = 0.12
    pivot.location = location
    coll.objects.link(pivot)
    return pivot


def parent_keep_transform(obj, pivot):
    obj.parent = pivot
    obj.matrix_parent_inverse = pivot.matrix_world.inverted()


def build_drone(coll, name="Drone", origin=(0, 0, 0), accent="Drone_Accent_A", folded=PROPS_FOLDED,
                arms_folded=ARMS_FOLDED, spec=None, with_battery=True, bottom_out=False):
    s = spec or SPECS["M"]
    k = s["detail"]
    arm_z = s["arm_z"]
    body_len, body_width, body_height = s["body"]
    tank_top, tank_bottom, tank_height = s["tank_top"], s["tank_bottom"], s["tank_h"]
    motor_radius = s["motor_r"]
    skid_z = 0.02
    ox, oy, oz = origin
    off = mathutils.Vector(origin)

    collected = []  # díly právě stavěného ramene, aby šly zavěsit pod jeho kloub

    def track(obj):
        collected.append(obj)
        return obj

    def loft(part, rings, mat, **kwargs):
        return track(add_loft(coll, f"{name}_{part}", [[p + off for p in ring] for ring in rings], mat, **kwargs))

    def tube(part, p0, p1, radii, mat, segments=TUBE_SEGMENTS, smooth=True):
        return loft(part, tube_rings(p0, p1, radii, segments=segments), mat, smooth=smooth)

    def box(part, dims, loc, mat, **kwargs):
        return track(set_material(
            parts.add_box(coll, f"{name}_{part}", dims, (ox + loc[0], oy + loc[1], oz + loc[2]), **kwargs), mat
        ))

    def cyl(part, radius, depth, loc, mat, **kwargs):
        return track(set_material(
            parts.add_cylinder(coll, f"{name}_{part}", radius, depth, (ox + loc[0], oy + loc[1], oz + loc[2]), **kwargs),
            mat,
        ))

    body_z = arm_z
    tank_top_z = body_z - body_height / 2 - 0.01
    tank_bottom_z = tank_top_z - tank_height
    bp = s["body_power"]

    # trup: zaoblená skříň, dole i nahoře zúžená
    body_profile = [
        (-body_height / 2, 0.86, bp + 1.0),
        (-body_height / 2 + 0.03, 0.97, bp + 0.5),
        (0.0, 1.0, bp),
        (body_height / 2 - 0.04, 0.95, bp + 0.2),
        (body_height / 2, 0.78, bp + 1.0),
    ]
    loft("Body", [
        superellipse_ring(body_len / 2 * sc, body_width / 2 * sc, body_z + dz, power=p)
        for dz, sc, p in body_profile
    ], "Drone_White")
    # barevný pás kolem trupu
    loft("BodyStripe", [
        superellipse_ring(body_len / 2 * 1.005, body_width / 2 * 1.005, body_z + dz, power=bp)
        for dz in (-0.012 * k, 0.012 * k)
    ], accent, cap_start=False, cap_end=False)

    # GPS věž s kopulí uprostřed trupu
    mast_r = 0.062 * k
    mast_h = s["mast_h"]
    mast_base = body_z + body_height / 2 - 0.01
    tube("GpsMast", (0, 0, mast_base), (0, 0, mast_base + mast_h), [mast_r] * 2, "Carbon", segments=16)
    loft("GpsDome", [
        circle_ring(mast_r * math.cos(math.radians(a)), mast_base + mast_h + 0.045 * k * math.sin(math.radians(a)), 16)
        for a in (0, 25, 50, 72, 90)
    ], "Drone_White", cap_end=False)
    for i in range(int(mast_h / 0.03 + 1e-6) - 1):  # chladicí prstence věže
        loft(f"GpsRib_{i}", [
            circle_ring(0.068 * k, mast_base + 0.03 + i * 0.03, 16),
            circle_ring(0.068 * k, mast_base + 0.042 + i * 0.03, 16),
        ], "Carbon", cap_start=False, cap_end=False)

    if with_battery:  # baterie zasunutá zezadu do trupu
        bat_x = -body_len / 2 + 0.08
        loft("Battery", [
            superellipse_ring(0.1, body_width / 2 * sc, body_z + dz, power=4.0)
            for dz, sc in ((-0.06, 0.82), (-0.04, 0.9), (0.04, 0.9), (0.06, 0.8))
        ], "Carbon", loc=(bat_x, 0, 0))
        box("BatteryLatch", (0.04, 0.14, 0.035), (bat_x - 0.09, 0, body_z + 0.05), accent)

    # nádrž: kónická skořepina s hrdlem a stavoznakem
    tank_rings = []
    for t, (scale, power) in enumerate(((1.0, 4.5), (0.99, 4.2), (0.92, 4.0), (0.84, 4.0), (0.8, 4.5))):
        z = tank_top_z - tank_height * t / 4
        ax = (tank_top[0] + (tank_bottom[0] - tank_top[0]) * t / 4) / 2
        by = (tank_top[1] + (tank_bottom[1] - tank_top[1]) * t / 4) / 2
        tank_rings.append(superellipse_ring(ax * scale, by * scale, z, power=power))
    loft("Tank", tank_rings, "Drone_White")
    tube("TankNeck", (0.1 * k, 0, tank_top_z), (0.1 * k, 0, tank_top_z + 0.055 * k), [0.085 * k, 0.078 * k], "Carbon",
         segments=16)
    loft("TankCap", [
        circle_ring(0.082 * k, tank_top_z + 0.055 * k, 16),
        circle_ring(0.086 * k, tank_top_z + 0.075 * k, 16),
        circle_ring(0.07 * k, tank_top_z + 0.088 * k, 16),
    ], accent)
    box("TankGauge", (0.02, 0.05, tank_height - 0.12), (tank_top[0] / 2 - 0.02, -0.16 * k, tank_top_z - tank_height / 2),
        "Glass_Dark")

    # čerpadlo a rozdělovač pod nádrží
    tube("Pump", (-0.11 * k, 0, tank_bottom_z - 0.03 * k), (0.11 * k, 0, tank_bottom_z - 0.03 * k),
         [0.05 * k, 0.062 * k, 0.062 * k, 0.05 * k], "Carbon", segments=14)
    box("Manifold", (0.16 * k, 0.1 * k, 0.05 * k), (0, 0, tank_bottom_z - 0.08 * k), "Carbon")

    # radar a kamery vpředu, zadní radar
    nose_x = body_len / 2
    loft("Nose", [
        superellipse_ring(0.05 * k * sc, 0.13 * k * sc, body_z + dz * k, power=4.0)
        for dz, sc in ((-0.055, 0.8), (-0.03, 1.0), (0.03, 1.0), (0.05, 0.85))
    ], "Carbon", loc=(nose_x, 0, 0))
    for i, cy_ in enumerate((-0.06 * k, 0.06 * k)):
        cyl(f"Lens_{i}", 0.025 * k, 0.02 * k, (nose_x + 0.04 * k, cy_, body_z), "Glass_Dark",
            rot=(0, math.radians(90), 0), verts=14)
    loft("RadarRear", [
        superellipse_ring(0.04 * k * sc, 0.1 * k * sc, body_z - 0.03 * k + dz * k, power=4.0)
        for dz, sc in ((-0.04, 0.8), (-0.02, 1.0), (0.02, 1.0), (0.04, 0.85))
    ], "Carbon", loc=(-nose_x, 0, 0))

    # ramena, gondoly, vrtule - každé rameno pod vlastním kloubem, aby šlo složit
    nozzle_no = 0
    for idx, (ax, ay) in enumerate(arm_positions(s), start=1):
        root = mathutils.Vector((math.copysign(body_len / 2 - 0.06 * k, ax), math.copysign(body_width / 2 - 0.06 * k, ay),
                                 body_z))
        tip = mathutils.Vector((ax, ay, arm_z + 0.05 * k))
        collected.clear()
        tube(f"Arm_{idx}", root, tip, [r * k for r in (0.055, 0.05, 0.044, 0.038, 0.036)], "Carbon")
        # objímky na obou koncích ramene
        for part, base, t0, t1 in ((f"ArmCollarRoot_{idx}", root, 0.04, 0.12), (f"ArmCollarTip_{idx}", tip, -0.14, -0.05)):
            d = (tip - root).normalized()
            tube(part, base + d * t0 * k, base + d * t1 * k, [r * k for r in (0.058, 0.062, 0.062, 0.058)], "Drone_White")
        # pružná spojka hadice v kloubu místo pevné vzpěry, která by skládání blokovala
        tube(f"ArmJoint_{idx}", root - (tip - root).normalized() * 0.05 * k, root + (tip - root).normalized() * 0.04 * k,
             [r * k for r in (0.05, 0.066, 0.066, 0.05)], "Carbon", segments=10)

        # gondola: spodní statorová část, žebra, horní kryt
        motor_z = tip.z + 0.07 * k
        loft(f"Motor_{idx}", [
            circle_ring(motor_radius * sc, motor_z + dz * k, 18)
            for dz, sc in ((-0.07, 0.75), (-0.055, 0.95), (-0.02, 1.0), (0.02, 1.0), (0.05, 0.92), (0.07, 0.7))
        ], "Carbon", loc=(ax, ay, 0))
        for r_i in range(3):
            loft(f"MotorRib_{idx}_{r_i}", [
                circle_ring(motor_radius * 1.06, motor_z + (-0.035 + r_i * 0.03) * k, 18),
                circle_ring(motor_radius * 1.06, motor_z + (-0.023 + r_i * 0.03) * k, 18),
            ], "Steel_Galvanized", loc=(ax, ay, 0), cap_start=False, cap_end=False)

        hubs = {"Top": motor_z + 0.1 * k, "Bottom": motor_z - 0.1 * k}
        hubs = {lv: hubs[lv] for lv in s["levels"]}
        for tag, hz in hubs.items():
            r = 0.045 * k
            loft(f"Hub{tag}_{idx}", [
                circle_ring(r * sc, hz + dz * k, 14) for dz, sc in ((-0.02, 0.85), (0, 1.0), (0.022, 0.8))
            ], "Drone_White", loc=(ax, ay, 0))

        arm_angle = math.atan2(ay, ax)
        for rotor, hz in hubs.items():
            for b in range(2):
                if folded:
                    # bottom_out: spodní listy ven podél ramene, ke středu by vjely do trupu
                    angle = arm_angle + (0.0 if bottom_out and rotor == "Bottom" else math.pi)
                    side = (1 if b == 0 else -1) * (s["blade"][1] * 0.55)
                else:
                    angle = b * math.pi + (0 if rotor == "Top" else math.pi / 2)
                    side = 0.0
                track(add_blade(coll, f"{name}_Blade_{idx}{rotor}{b}", (ox + ax, oy + ay, oz + hz), angle, side,
                                up=(rotor == "Top"), blade=s["blade"]))

        # hadice podél ramene a rozprašovač pod gondolou (nebo na rameni postřiku vně motoru)
        if idx in s["nozzles"]:
            hose_drop = 0.055 * k
            hose_r = 0.013 * k
            tube(f"Hose_{idx}", (root.x, root.y, root.z - hose_drop), (ax, ay, tip.z - hose_drop), [hose_r, hose_r],
                 "Carbon", segments=8)
            ny = ay if s["nozzle_y"] is None else math.copysign(s["nozzle_y"], ay)
            if s["boom"]:
                bz = tip.z - hose_drop
                tube(f"SprayBoom_{idx}", (ax, ay - math.copysign(0.02, ay), bz), (ax, ny, bz), [0.022 * k, 0.018 * k],
                     "Carbon", segments=10)
                tube(f"SprayBoomStay_{idx}", (ax, ay, tip.z - 0.02 * k), (ax, ny - math.copysign(0.03, ay), bz),
                     [0.01 * k, 0.01 * k], "Carbon", segments=8)
            nozzle_z = tip.z - hose_drop - 0.07 * k
            tube(f"NozzleDrop_{idx}", (ax, ny, tip.z - hose_drop), (ax, ny, nozzle_z + 0.02 * k), [hose_r, hose_r],
                 "Carbon", segments=8)
            loft(f"Nozzle_{idx}", [
                circle_ring(r * k, nozzle_z + dz * k, 12)
                for dz, r in ((0.02, 0.02), (-0.01, 0.026), (-0.03, 0.042), (-0.042, 0.038))
            ], accent, loc=(ax, ny, 0))
            nozzle_no += 1
            outlet = bpy.data.objects.new(f"{name}_SprayNozzle_{nozzle_no}", None)
            outlet.empty_display_type = "PLAIN_AXES"
            outlet.empty_display_size = 0.05
            outlet.location = off + mathutils.Vector((ax, ny, nozzle_z - 0.042 * k))
            coll.objects.link(outlet)
            track(outlet)

        arm_objs = list(collected)
        pivot = add_arm_pivot(coll, f"{name}_ArmPivot_{idx}", off + root)
        bpy.context.view_layer.update()
        for obj in arm_objs:
            parent_keep_transform(obj, pivot)
        # rotace až po zavěšení, jinak by ji parent inverse hned vyrušil
        base_az = math.atan2(ay - root.y, ax - root.x)
        fold_front, fold_rear = (math.radians(a) for a in s["fold"])
        target_az = math.copysign(fold_front if ax > 0 else fold_rear, ay)
        pivot.rotation_euler = (0, 0, (target_az - base_az) * arms_folded)

    # podvozek: šikmé nohy s patkami a podélná lyžina
    skid_y, skid_half, leg_x = s["skid"]
    for side, sy in (("L", 1), ("R", -1)):
        y_out = sy * skid_y
        for tag, lx in (("F", leg_x), ("R", -leg_x)):
            top = (lx * 0.55, sy * (tank_bottom[1] / 2 - 0.02), tank_bottom_z + 0.06)
            bottom = (lx, y_out, skid_z + 0.03)
            tube(f"Leg_{side}{tag}", top, bottom, [r * k for r in (0.032, 0.028, 0.026)], "Drone_White", segments=10)
        tube(f"Skid_{side}", (-skid_half, y_out, skid_z), (skid_half, y_out, skid_z), [r * k for r in (0.024, 0.03, 0.03, 0.024)],
             "Drone_White", segments=10)
        for tag, lx in (("F", skid_half - 0.04), ("R", -skid_half + 0.04)):
            loft(f"SkidPad_{side}{tag}", [
                circle_ring(r * k, skid_z - 0.03 + dz * k, 12) for dz, r in ((0, 0.034), (0.02, 0.04), (0.04, 0.032))
            ], "Carbon", loc=(lx, y_out, 0))
        box(f"NavLight_{side}", (0.05, 0.03, 0.02), (skid_half - 0.06, y_out, skid_z + 0.04),
            "Lamp_Green" if sy > 0 else "Lamp_Red")
    tube("SkidCross", (0, skid_y, skid_z), (0, -skid_y, skid_z), [r * k for r in (0.022, 0.026, 0.022)], "Drone_White",
         segments=10)


def add_blade(coll, name, hub, angle, side_offset, up=True, stations=7, blade=None):
    """List vrtule: tětiva se zužuje ke špičce a profil se po délce zkrucuje."""
    length, chord_root, chord_tip = blade or SPECS["M"]["blade"]
    twist_max = math.radians(9)
    rings = []
    for i in range(stations):
        t = i / (stations - 1)
        r = 0.05 + (length - 0.05) * t
        chord = chord_root + (chord_tip - chord_root) * t
        thick = (0.013 if t < 0.15 else 0.008) * (1.0 - 0.35 * t)
        twist = twist_max * (1.0 - t) * (1 if up else -1)
        ring = []
        for k in range(8):
            a = 2 * math.pi * k / 8
            cx = chord / 2 * math.copysign(abs(math.cos(a)) ** 0.5, math.cos(a))
            cz = thick / 2 * math.copysign(abs(math.sin(a)) ** 0.5, math.sin(a))
            # profil se naklápí kolem podélné osy listu
            x = r
            y = cx * math.cos(twist) - cz * math.sin(twist)
            z = cx * math.sin(twist) + cz * math.cos(twist)
            ring.append(mathutils.Vector((x, y + side_offset, z)))
        rings.append(ring)

    obj = add_loft(coll, name, rings, "Carbon")
    obj.location = hub
    obj.rotation_euler = (0, 0, angle)
    return obj


PARK_X = 2.1  # rozteč parkovacích míst na plošině


def platform_top_z():
    """Horní hrana plošiny vleku - ať drony sedí správně i po změně jeho rozměrů."""
    return parts.PLATFORM_Z + parts.PLATFORM_THICK / 2


def build(on_trailer=True):
    coll = clear_collection()
    # na vleku drony parkují se složenými rameny i vrtulemi, vizuálně odlišené barvou
    z = platform_top_z() + 0.015 if on_trailer else 0.0
    build_drone(coll, name="Drone_A", origin=(PARK_X, 0, z), accent="Drone_Accent_A", arms_folded=1.0)
    build_drone(coll, name="Drone_B", origin=(-PARK_X, 0, z), accent="Drone_Accent_B", arms_folded=1.0)
    bpy.context.view_layer.update()
    print(f"Drone built: {len(coll.objects)} objects in '{COLLECTION_NAME}'")


if __name__ == "__main__":
    build()
