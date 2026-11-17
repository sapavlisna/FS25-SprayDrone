"""Parametricky postaví postřikový dron (předloha DJI Agras T50, viz PLAN.md).

Rozměry v konfiguraci "ramena rozložená": 1590 x 1900 mm, výška 820 mm, nádrž 40 l.
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

# --- Parametry (m) ---
ARM_SPAN_X = 1.59
ARM_SPAN_Y = 1.90
ARM_Z = 0.56  # tak vysoko, aby nádrž ani rozdělovač nevisely pod lyžinami
BODY_LEN = 0.56
BODY_WIDTH = 0.50
BODY_HEIGHT = 0.17
TANK_TOP = (0.58, 0.48)
TANK_BOTTOM = (0.44, 0.36)
TANK_HEIGHT = 0.30
BLADE_LEN = 0.68
BLADE_CHORD_ROOT = 0.095
BLADE_CHORD_TIP = 0.045
BLADE_TWIST = math.radians(9)
MOTOR_RADIUS = 0.075
SKID_Z = 0.02
PROPS_FOLDED = True
ARMS_FOLDED = 0.0  # 0 = rozloženo, 1 = složeno podél trupu

# azimut ramene po složení (přední se srovnají víc, ať se gondoly nepotkají)
FOLD_TARGET_FRONT = math.radians(160)
FOLD_TARGET_REAR = math.radians(176)

RING_SEGMENTS = 20
TUBE_SEGMENTS = 12


def clear_collection():
    if COLLECTION_NAME in bpy.data.collections:
        coll = bpy.data.collections[COLLECTION_NAME]
        for obj in list(coll.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
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


def arm_positions():
    return [
        (sx * ARM_SPAN_X / 2, sy * ARM_SPAN_Y / 2)
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
                arms_folded=ARMS_FOLDED):
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

    body_z = ARM_Z
    tank_top_z = body_z - BODY_HEIGHT / 2 - 0.01
    tank_bottom_z = tank_top_z - TANK_HEIGHT

    # trup: zaoblená skříň, dole i nahoře zúžená
    body_profile = [
        (-BODY_HEIGHT / 2, 0.86, 5.0),
        (-BODY_HEIGHT / 2 + 0.03, 0.97, 4.5),
        (0.0, 1.0, 4.0),
        (BODY_HEIGHT / 2 - 0.04, 0.95, 4.2),
        (BODY_HEIGHT / 2, 0.78, 5.0),
    ]
    loft("Body", [
        superellipse_ring(BODY_LEN / 2 * s, BODY_WIDTH / 2 * s, body_z + dz, power=p)
        for dz, s, p in body_profile
    ], "Drone_White")
    # barevný pás kolem trupu
    loft("BodyStripe", [
        superellipse_ring(BODY_LEN / 2 * 1.005, BODY_WIDTH / 2 * 1.005, body_z + dz, power=4.0)
        for dz in (-0.012, 0.012)
    ], accent, cap_start=False, cap_end=False)

    # GPS věž s kopulí uprostřed trupu
    mast_base = body_z + BODY_HEIGHT / 2 - 0.01
    tube("GpsMast", (0, 0, mast_base), (0, 0, mast_base + 0.15), [0.062] * 2, "Carbon", segments=16)
    loft("GpsDome", [
        circle_ring(0.062 * math.cos(math.radians(a)), mast_base + 0.15 + 0.045 * math.sin(math.radians(a)), 16)
        for a in (0, 25, 50, 72, 90)
    ], "Drone_White", cap_end=False)
    for i in range(4):  # chladicí prstence věže
        loft(f"GpsRib_{i}", [
            circle_ring(0.068, mast_base + 0.03 + i * 0.03, 16),
            circle_ring(0.068, mast_base + 0.042 + i * 0.03, 16),
        ], "Carbon", cap_start=False, cap_end=False)

    # baterie zasunutá zezadu do trupu
    bat_x = -BODY_LEN / 2 + 0.08
    loft("Battery", [
        superellipse_ring(0.1, BODY_WIDTH / 2 * s, body_z + dz, power=4.0)
        for dz, s in ((-0.06, 0.82), (-0.04, 0.9), (0.04, 0.9), (0.06, 0.8))
    ], "Carbon", loc=(bat_x, 0, 0))
    box("BatteryLatch", (0.04, 0.14, 0.035), (bat_x - 0.09, 0, body_z + 0.05), accent)

    # nádrž: kónická skořepina s hrdlem a stavoznakem
    tank_rings = []
    for t, (scale, power) in enumerate(((1.0, 4.5), (0.99, 4.2), (0.92, 4.0), (0.84, 4.0), (0.8, 4.5))):
        z = tank_top_z - TANK_HEIGHT * t / 4
        ax = (TANK_TOP[0] + (TANK_BOTTOM[0] - TANK_TOP[0]) * t / 4) / 2
        by = (TANK_TOP[1] + (TANK_BOTTOM[1] - TANK_TOP[1]) * t / 4) / 2
        tank_rings.append(superellipse_ring(ax * scale, by * scale, z, power=power))
    loft("Tank", tank_rings, "Drone_White")
    tube("TankNeck", (0.1, 0, tank_top_z), (0.1, 0, tank_top_z + 0.055), [0.085, 0.078], "Carbon", segments=16)
    loft("TankCap", [
        circle_ring(0.082, tank_top_z + 0.055, 16),
        circle_ring(0.086, tank_top_z + 0.075, 16),
        circle_ring(0.07, tank_top_z + 0.088, 16),
    ], accent)
    box("TankGauge", (0.02, 0.05, TANK_HEIGHT - 0.12), (TANK_TOP[0] / 2 - 0.02, -0.16, tank_top_z - TANK_HEIGHT / 2),
        "Glass_Dark")

    # čerpadlo a rozdělovač pod nádrží
    tube("Pump", (-0.11, 0, tank_bottom_z - 0.03), (0.11, 0, tank_bottom_z - 0.03), [0.05, 0.062, 0.062, 0.05],
         "Carbon", segments=14)
    box("Manifold", (0.16, 0.1, 0.05), (0, 0, tank_bottom_z - 0.08), "Carbon")

    # radar a kamery vpředu, zadní radar
    nose_x = BODY_LEN / 2
    loft("Nose", [
        superellipse_ring(0.05 * s, 0.13 * s, body_z + dz, power=4.0)
        for dz, s in ((-0.055, 0.8), (-0.03, 1.0), (0.03, 1.0), (0.05, 0.85))
    ], "Carbon", loc=(nose_x, 0, 0))
    for i, cy_ in enumerate((-0.06, 0.06)):
        cyl(f"Lens_{i}", 0.025, 0.02, (nose_x + 0.04, cy_, body_z), "Glass_Dark",
            rot=(0, math.radians(90), 0), verts=14)
    loft("RadarRear", [
        superellipse_ring(0.04 * s, 0.1 * s, body_z - 0.03 + dz, power=4.0)
        for dz, s in ((-0.04, 0.8), (-0.02, 1.0), (0.02, 1.0), (0.04, 0.85))
    ], "Carbon", loc=(-nose_x, 0, 0))

    # ramena, gondoly, vrtule - každé rameno pod vlastním kloubem, aby šlo složit
    for idx, (ax, ay) in enumerate(arm_positions(), start=1):
        root = mathutils.Vector((math.copysign(BODY_LEN / 2 - 0.06, ax), math.copysign(BODY_WIDTH / 2 - 0.06, ay), body_z))
        tip = mathutils.Vector((ax, ay, ARM_Z + 0.05))
        collected.clear()
        tube(f"Arm_{idx}", root, tip, [0.055, 0.05, 0.044, 0.038, 0.036], "Carbon")
        # objímky na obou koncích ramene
        for part, base, t0, t1 in ((f"ArmCollarRoot_{idx}", root, 0.04, 0.12), (f"ArmCollarTip_{idx}", tip, -0.14, -0.05)):
            d = (tip - root).normalized()
            tube(part, base + d * t0, base + d * t1, [0.058, 0.062, 0.062, 0.058], "Drone_White")
        # pružná spojka hadice v kloubu místo pevné vzpěry, která by skládání blokovala
        tube(f"ArmJoint_{idx}", root - (tip - root).normalized() * 0.05, root + (tip - root).normalized() * 0.04,
             [0.05, 0.066, 0.066, 0.05], "Carbon", segments=10)

        # gondola: spodní statorová část, žebra, horní kryt
        motor_z = tip.z + 0.07
        loft(f"Motor_{idx}", [
            circle_ring(MOTOR_RADIUS * s, motor_z + dz, 18)
            for dz, s in ((-0.07, 0.75), (-0.055, 0.95), (-0.02, 1.0), (0.02, 1.0), (0.05, 0.92), (0.07, 0.7))
        ], "Carbon", loc=(ax, ay, 0))
        for r_i in range(3):
            loft(f"MotorRib_{idx}_{r_i}", [
                circle_ring(MOTOR_RADIUS * 1.06, motor_z - 0.035 + r_i * 0.03, 18),
                circle_ring(MOTOR_RADIUS * 1.06, motor_z - 0.023 + r_i * 0.03, 18),
            ], "Steel_Galvanized", loc=(ax, ay, 0), cap_start=False, cap_end=False)

        hub_top_z = motor_z + 0.1
        hub_bottom_z = motor_z - 0.1
        for tag, hz, r in (("Top", hub_top_z, 0.045), ("Bottom", hub_bottom_z, 0.045)):
            loft(f"Hub{tag}_{idx}", [
                circle_ring(r * s, hz + dz, 14) for dz, s in ((-0.02, 0.85), (0, 1.0), (0.022, 0.8))
            ], "Drone_White", loc=(ax, ay, 0))

        arm_angle = math.atan2(ay, ax)
        for rotor, hz in (("Top", hub_top_z), ("Bottom", hub_bottom_z)):
            for b in range(2):
                if folded:
                    angle = arm_angle + math.pi
                    side = (1 if b == 0 else -1) * (BLADE_CHORD_ROOT * 0.55)
                else:
                    angle = b * math.pi + (0 if rotor == "Top" else math.pi / 2)
                    side = 0.0
                track(add_blade(coll, f"{name}_Blade_{idx}{rotor}{b}", (ox + ax, oy + ay, oz + hz), angle, side,
                                up=(rotor == "Top")))

        # hadice podél ramene a rozprašovač pod gondolou
        hose_drop = 0.055
        tube(f"Hose_{idx}", (root.x, root.y, root.z - hose_drop), (ax, ay, tip.z - hose_drop), [0.013, 0.013],
             "Carbon", segments=8)
        nozzle_z = tip.z - hose_drop - 0.07
        tube(f"NozzleDrop_{idx}", (ax, ay, tip.z - hose_drop), (ax, ay, nozzle_z + 0.02), [0.013, 0.013],
             "Carbon", segments=8)
        loft(f"Nozzle_{idx}", [
            circle_ring(r, nozzle_z + dz, 12) for dz, r in ((0.02, 0.02), (-0.01, 0.026), (-0.03, 0.042), (-0.042, 0.038))
        ], accent, loc=(ax, ay, 0))

        arm_objs = list(collected)
        pivot = add_arm_pivot(coll, f"{name}_ArmPivot_{idx}", off + root)
        bpy.context.view_layer.update()
        for obj in arm_objs:
            parent_keep_transform(obj, pivot)
        # rotace až po zavěšení, jinak by ji parent inverse hned vyrušil
        base_az = math.atan2(ay - root.y, ax - root.x)
        target_az = math.copysign(FOLD_TARGET_FRONT if ax > 0 else FOLD_TARGET_REAR, ay)
        pivot.rotation_euler = (0, 0, (target_az - base_az) * arms_folded)

    # podvozek: šikmé nohy s patkami a podélná lyžina
    for side, sy in (("L", 1), ("R", -1)):
        y_out = sy * 0.42
        for tag, lx in (("F", 0.3), ("R", -0.3)):
            top = (lx * 0.55, sy * (TANK_BOTTOM[1] / 2 - 0.02), tank_bottom_z + 0.06)
            bottom = (lx, y_out, SKID_Z + 0.03)
            tube(f"Leg_{side}{tag}", top, bottom, [0.032, 0.028, 0.026], "Drone_White", segments=10)
        tube(f"Skid_{side}", (-0.46, y_out, SKID_Z), (0.46, y_out, SKID_Z), [0.024, 0.03, 0.03, 0.024],
             "Drone_White", segments=10)
        for tag, lx in (("F", 0.42), ("R", -0.42)):
            loft(f"SkidPad_{side}{tag}", [
                circle_ring(r, SKID_Z - 0.03 + dz, 12) for dz, r in ((0, 0.034), (0.02, 0.04), (0.04, 0.032))
            ], "Carbon", loc=(lx, y_out, 0))
        box(f"NavLight_{side}", (0.05, 0.03, 0.02), (0.4, y_out, SKID_Z + 0.04),
            "Lamp_Green" if sy > 0 else "Lamp_Red")
    tube("SkidCross", (0, 0.42, SKID_Z), (0, -0.42, SKID_Z), [0.022, 0.026, 0.022], "Drone_White", segments=10)


def add_blade(coll, name, hub, angle, side_offset, up=True, stations=7):
    """List vrtule: tětiva se zužuje ke špičce a profil se po délce zkrucuje."""
    rings = []
    for i in range(stations):
        t = i / (stations - 1)
        r = 0.05 + (BLADE_LEN - 0.05) * t
        chord = BLADE_CHORD_ROOT + (BLADE_CHORD_TIP - BLADE_CHORD_ROOT) * t
        thick = (0.013 if t < 0.15 else 0.008) * (1.0 - 0.35 * t)
        twist = BLADE_TWIST * (1.0 - t) * (1 if up else -1)
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
