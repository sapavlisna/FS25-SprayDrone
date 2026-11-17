"""Oj vleků jako samostatné díly knihovny (parts_lib): oj do A s nájezdovou brzdou a kulovou hlavou za auto (Middle a Mini, liší
se délkou) a plochý A-rám podle Farmtech DPW 1800 se spojkou za traktor nebo za auto (Max). Součástí každého dílu je podpěrné
kolečko (pohyblivá skupina jockeyWheel, kterou animace moveSupport zvedá, s kolizí colJockeyWheel) a attacherJoint ve středu
spojky.

Díl se staví na svém místě (souřadnice Y jsou ve vleku) a pak se posune tak, aby jeho počátek byl na čele rámu (x 0, y base_y0,
z 0); do vleku se umístí PL.Place.at(0, base_y0, 0). Rozměry vleku (výška paluby, poloha čela a spojky) přicházejí jako parametry.
"""

import math
import types

import bmesh
import bpy
from mathutils import Matrix, Vector

import parts_lib as PL
import sdt_parts as P

box, tube, cylinder_x, cylinder_z, empty = P.box, P.tube, P.cylinder_x, P.cylinder_z, P.empty

COL_VEHICLE = (0x10004, 0xfe3ffb83)


def _collision_box(name, parent, x0, x1, y0, y1, z0, z1, group_mask, **props):
    """Neviditelný kolizní kvádr s počátkem v rodiči (vrcholy leží přímo na místě)."""
    obj = box(name, x0, x1, y0, y1, z0, z1, "SDT_Frame")
    world = obj.matrix_world.copy()
    obj.data.transform(world)
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_world = parent.matrix_world.copy() if parent else Matrix.Identity(4)
    obj.data.transform(obj.matrix_world.inverted())
    obj.display_type = "WIRE"
    obj.hide_render = True
    for k, v in dict(collisionFilterGroup=str(group_mask[0]), collisionFilterMask=str(group_mask[1]), nonRenderable=True,
                     **props).items():
        obj["i3D_" + k] = v
    return obj


def _adopt(parent, objs):
    for o in objs:
        w = o.matrix_world.copy()
        o.parent = parent
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_world = w


def _jockey_collision(pivot, jx, jy, jockey_col):
    cx, cy, cz = jockey_col
    _collision_box("colJockeyWheel", pivot, jx - cx, jx + cx, jy - cy, jy + cy, 0.0, cz, COL_VEHICLE,
                   compoundChild=True, density=0.001)


# ------------------------------------------------------------------------------------------------------ oj za auto (Middle, Mini)
def _car_coupler(base_y0, coupler_y, coupler_z, drawbar_z, root_x, deck_top, tip):
    """Nájezdová brzda s kulovou hlavou (styl přívěsů za auto): střed koule tažného zařízení = attacherJoint
    (0, coupler_y, coupler_z). Hlava s rukojetí a ukazatelem opotřebení, táhlo v gumovém měchu, skříň nájezdu na
    vrcholu oje, ruční brzda s pákou a plynovou vzpěrou, táhlo brzdy, pojistné lanko s karabinou a kabel 13pin
    se zástrčkou. Jen vizuál: kolize colDrawbar a geometrie tažení se nemění. Rozměry nájezdu jsou vztažené ke spojce."""
    by, bz = coupler_y, coupler_z
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
    hy0, hy1 = y1, by + 0.67
    P.loft_y("Coupler_Housing", [
        (hy0, 0.046, az - 0.050, az + 0.050, 6.0), (hy0 + 0.02, 0.052, az - 0.055, az + 0.055, 6.0),
        (hy1 - 0.07, 0.052, az - 0.058, az + 0.058, 6.0), (hy1, 0.044, az - 0.040, az + 0.040, 5.0)], "SDT_Steel")
    for side, sx in (("L", 1), ("R", -1)):
        box(f"Coupler_Flange_{side}", sx * 0.050, sx * 0.058, by + 0.29, by + 0.59, az - 0.07, az + 0.06, "SDT_Steel")
        for k, fy in enumerate((by + 0.35, by + 0.53)):
            cylinder_x(f"Coupler_Bolt_{side}{k}", (sx * 0.062, fy, az), 0.011, 0.01, "SDT_Steel", segments=6)
    top = az + 0.058
    px, py = 0.0, by + 0.50
    box("Coupler_BrakePivot", px - 0.022, px + 0.022, py - 0.03, py + 0.03, top - 0.005, top + 0.03, "SDT_Steel")
    lever_end = Vector((px, by + 0.77, top + 0.19))
    tube("Coupler_BrakeLever", (px, py, top + 0.02), lever_end, 0.013, "SDT_Frame", segments=10)
    grip_dir = (lever_end - Vector((px, py, top + 0.02))).normalized()
    tube("Coupler_BrakeGrip", lever_end - grip_dir * 0.03, lever_end + grip_dir * 0.07, 0.019, "SDT_Rubber", segments=12)
    lever_mid = Vector((px, py, top + 0.02)).lerp(lever_end, 0.4)
    spring_foot = Vector((0.03, by + 0.31, az + 0.035))
    tube("Coupler_GasSpring", spring_foot, spring_foot.lerp(lever_mid, 0.6), 0.011, "SDT_Frame", segments=10)
    tube("Coupler_GasSpringRod", spring_foot.lerp(lever_mid, 0.6), lever_mid, 0.005, "SDT_Steel", segments=8)
    tube("Coupler_BrakeRod", (0, hy1 + 0.005, az - 0.01), (0, base_y0 - 0.02, az - 0.01), 0.008, "SDT_Steel", segments=8)
    cable = P.hermite_path([(0.024, py + 0.02, top + 0.02), (0.06, by + 0.48, az + 0.04), (0.075, by + 0.33, az - 0.04),
                            (0.07, by + 0.18, bz - 0.07), (0.045, by + 0.07, bz - 0.095), (0.035, by + 0.045, bz - 0.10)],
                           samples=10)
    P.sweep("Coupler_BreakawayCable", cable, 0.0035, "SDT_Steel", segments=6)
    end = cable[-1]
    ring = [end + Vector((0, 0.018 * math.sin(a), -0.018 - 0.028 * math.cos(a)))
            for a in (2 * math.pi * k / 16 for k in range(17))]
    P.sweep("Coupler_Carabiner", ring, 0.0035, "SDT_Steel", segments=6)

    root = Vector((root_x, base_y0 + 0.40, drawbar_z))
    along = [root.lerp(tip, t) + Vector((-0.012, 0, 0.07)) for t in (0.3, 0.55, 0.8)]
    plug_a, plug_b = Vector((0.08, by + 0.25, bz - 0.005)), Vector((0.074, by + 0.16, bz - 0.04))
    wire = P.hermite_path([(0.42, base_y0 + 0.03, deck_top - 0.12)] + [tuple(p) for p in along] +
                          [(0.09, by + 0.37, bz + 0.02), tuple(plug_a)], samples=10)
    P.sweep("Coupler_13PinCable", wire, 0.006, "SDT_HoseBlack", segments=8)
    d = (plug_b - plug_a).normalized()
    tube("Coupler_13PinPlug", plug_a - d * 0.01, plug_b, 0.021, "SDT_Plastic", segments=14)
    tube("Coupler_13PinCap", plug_b, plug_b + d * 0.012, 0.024, "SDT_ChargerGrey", segments=14)
    box("Coupler_13PinDock", 0.40, 0.46, base_y0 - 0.005, base_y0 + 0.001, deck_top - 0.16, deck_top - 0.08, "SDT_Plastic")


def part_drawbar_car(base_y0, coupler_y, jockey_y, coupler_z, drawbar_z, root_x, jockey_x, jockey_col, deck_top, deck_plate):
    """Oj do A za auto: dvě trubky z čela rámu ke hrotu, kulová hlava s nájezdovou brzdou, podpěrné kolečko a attacherJoint
    (Middle a Mini, liší se jen vzdáleností spojky od čela rámu)."""
    tip = Vector((0, coupler_y + 0.25, drawbar_z))
    for side, sx in (("L", 1), ("R", -1)):
        root = Vector((sx * root_x, base_y0 + 0.40, drawbar_z))
        tube(f"Drawbar_{side}", root, tip, 0.045, "SDT_Frame", segments=8)
        box(f"DrawbarMount_{side}", root.x - 0.06, root.x + 0.06, base_y0, base_y0 + 0.45,
            drawbar_z - 0.05, deck_top - deck_plate, "SDT_Frame")
    _car_coupler(base_y0, coupler_y, coupler_z, drawbar_z, root_x, deck_top, tip)
    jx, jy = jockey_x, jockey_y
    box("Jockey_Clamp", jx - 0.14, jx + 0.04, jy - 0.05, jy + 0.05, drawbar_z - 0.04, drawbar_z + 0.06, "SDT_Frame")
    moving = [
        tube("Jockey_Tube", (jx, jy, 0.20), (jx, jy, drawbar_z + 0.30), 0.03, "SDT_Steel", segments=12),
        tube("Jockey_Crank", (jx, jy, drawbar_z + 0.30), (jx, jy, drawbar_z + 0.36), 0.012, "SDT_Frame", segments=8),
        box("Jockey_Fork", jx - 0.05, jx + 0.05, jy - 0.03, jy + 0.03, 0.08, 0.21, "SDT_Steel"),
        cylinder_x("Jockey_Wheel", (jx, jy, 0.10), 0.10, 0.07, "SDT_Rubber", segments=20),
    ]
    pivot = empty("jockeyWheel", (jx, jy, drawbar_z))
    _adopt(pivot, moving)
    _jockey_collision(pivot, jx, jy, jockey_col)
    # vanilla přívěsy mají attacherJoint v i3d natočený "0 90 0" (osa Y i3d = osa Z Blenderu)
    aj = empty("attacherJoint", (0, coupler_y, coupler_z))
    aj.rotation_euler = (0, 0, math.radians(90))
    PL.localize((0, base_y0, 0))


# ------------------------------------------------------------------------------------------------------------- oj Max (DPW 1800)
def _flat_beam(name, p0, p1, w, z0, z1, mat):
    """Vodorovná hranatá pásnice šířky w mezi body p0 a p1 (x, y), ve výšce z0..z1; konce kolmé na osu."""
    a, b = Vector((p0[0], p0[1])), Vector((p1[0], p1[1]))
    d = (b - a).normalized()
    n = Vector((-d.y, d.x)) * (w / 2)
    quad = [a + n, b + n, b - n, a - n]
    bm = bmesh.new()
    lo = [bm.verts.new((q.x, q.y, z0)) for q in quad]
    hi = [bm.verts.new((q.x, q.y, z1)) for q in quad]
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return P._finish(name, bm, Matrix.Identity(4), mat)


def _drawbar_x(c, y):
    """Osa pásnice A-rámu (kladná strana) v místě y: přímka z kořene ke konci sbíhání."""
    y_root, y_conv = c.base_y0 + 0.05, c.coupler_y + c.converge
    t = (y - y_root) / (y_conv - y_root)
    return c.root_x + t * (c.tip_x - c.root_x)


def _chain(name, p0, p1, sag, pitch=0.042, wire=0.0045):
    """Řetěz z oválných článků prověšený mezi p0 a p1 (parabola), články střídavě ve svislé a vodorovné rovině."""
    p0, p1 = Vector(p0), Vector(p1)
    path = [p0.lerp(p1, t) + Vector((0, 0, -4 * sag * t * (1 - t))) for t in (i / 40 for i in range(41))]
    pts = P.resample(path, max(int(P.path_length(path) / pitch), 2) + 1)
    links = []
    for k in range(len(pts) - 1):
        a, b = pts[k], pts[k + 1]
        d = (b - a).normalized()
        side = d.cross(Vector((0, 0, 1))).normalized() if k % 2 == 0 else Vector((0, 0, 1)).cross(d).cross(d).normalized()
        cc = (a + b) / 2
        half = (b - a).length / 2 + wire * 1.5
        ring = [cc + d * half * math.cos(t) + side * 0.011 * math.sin(t) for t in (2 * math.pi * i / 14 for i in range(15))]
        links.append(P.sweep(f"{name}_L{k}", ring, wire, "SDT_Steel", segments=6))
    return P.merge(name, links)


def _coupling_head(name, pos, along, mat, hose_from=None):
    """Spojka vzduchové / elektrické hadice zaparkovaná v držáku: tělo spojky, víčko, kousek hadice k držáku."""
    pos, along = Vector(pos), Vector(along).normalized()
    parts = [tube(f"{name}_Body", pos - along * 0.030, pos + along * 0.022, 0.017, mat, segments=12),
             tube(f"{name}_Lip", pos + along * 0.022, pos + along * 0.030, 0.021, mat, segments=12),
             box(f"{name}_Palm", pos.x - 0.006, pos.x + 0.006, pos.y - 0.020, pos.y + 0.020, pos.z - 0.030, pos.z - 0.012,
                 mat)]
    if hose_from is not None:
        start = Vector(hose_from)
        mid = start.lerp(pos - along * 0.03, 0.5) + Vector((0, 0, -0.07))
        parts.append(P.sweep(f"{name}_Hose", P.hermite_path([tuple(start), tuple(mid), tuple(pos - along * 0.03)],
                                                            samples=8), 0.0085, "SDT_HoseBlack", segments=8))
    return P.merge(name, parts)


def _max_tractor(c, y_conv, z0, z1, extra=()):
    """Varianta za traktor / nákladní auto (konfigurace TRACTOR, skupina drawbarTractorSet): tažné oko na přírubě se čtyřmi
    šrouby, pojistný řetěz s hákem pod hlavou, držák vzduchových spojek (airIn červená, airOut žlutá) s vedením podél
    pravé pásnice. Uzly airIn / airOut jsou začátky hadic, které hra kreslí k tahači; *_detached jsou zaparkované spojky."""
    steel = "SDT_Steel"
    parts = []
    cy, cz = c.coupler_y, c.coupler_z
    hy0 = cy + 0.07
    parts.append(P.ring_z("Drawbar_Eye", (0, cy, cz), 0.042, 0.078, 0.05, steel))
    parts.append(_flat_beam("Drawbar_EyeNeck", (0, hy0 + 0.02), (0, cy + 0.02), 0.06, cz - 0.025, cz + 0.025, steel))
    for k, (fy0, fy1) in enumerate(((hy0 - 0.004, hy0 + 0.014), (hy0 + 0.018, hy0 + 0.036))):
        parts.append(box(f"Drawbar_EyeFlange{k}", -0.072, 0.072, fy0, fy1, cz - 0.062, cz + 0.062,
                         "SDT_CastIron" if k == 0 else "SDT_Frame"))
    for bx in (-0.050, 0.050):
        for bz in (-0.040, 0.040):
            cc = Vector((bx, hy0, cz + bz))
            parts.append(tube(f"Drawbar_EyeBolt{bx:+.2f}{bz:+.2f}", cc + Vector((0, -0.016, 0)), cc + Vector((0, 0.05, 0)),
                              0.009, steel, segments=6))
            parts.append(tube(f"Drawbar_EyeNut{bx:+.2f}{bz:+.2f}", cc + Vector((0, -0.024, 0)), cc + Vector((0, -0.010, 0)),
                              0.015, steel, segments=6))

    lug = Vector((0, cy + 0.22, z0 - 0.012))
    hook = Vector((0, y_conv + 0.06, z0 - 0.012))
    parts.append(box("Drawbar_ChainLug", -0.012, 0.012, lug.y - 0.025, lug.y + 0.025, z0 - 0.035, z0, steel))
    parts.append(box("Drawbar_HookLug", -0.012, 0.012, hook.y - 0.025, hook.y + 0.025, z0 - 0.035, z0, steel))
    parts.append(_chain("Drawbar_Chain", lug + Vector((0, 0, -0.03)), hook + Vector((0, 0, -0.07)), 0.12))
    hook_path = [hook + Vector((0, 0, -0.02)), hook + Vector((0, 0, -0.07)), hook + Vector((0, -0.025, -0.10)),
                 hook + Vector((0, -0.045, -0.075)), hook + Vector((0, -0.040, -0.055))]
    parts.append(P.sweep("Drawbar_ChainHook", P.hermite_path([tuple(p) for p in hook_path], samples=6), 0.008, steel,
                         segments=8))

    by0, by1 = y_conv - 0.035, y_conv - 0.015
    top = z1 + 0.012
    parts.append(box("Drawbar_AirBracket", -0.115, -0.010, by0, by1, top, top + 0.110, "SDT_Frame"))
    parts.append(box("Drawbar_AirBracketFoot", -0.115, -0.010, by0, by1 + 0.06, top, top + 0.008, "SDT_Frame"))
    lines = []
    for tag, x, mat in (("airIn", -0.085, "SDT_PaintRed"), ("airOut", -0.040, "SDT_PaintYellow")):
        z = top + 0.075
        parts.append(tube(f"{tag}_Socket", (x, by0 - 0.028, z), (x, by1, z), 0.016, mat, segments=12))
        parts.append(tube(f"{tag}_SocketLid", (x, by0 - 0.034, z), (x, by0 - 0.028, z), 0.019, "SDT_Rubber", segments=12))
        empty(tag, (x, by0 - 0.034, z))
        _coupling_head(f"{tag}_detached", (x, by1 + 0.095, top + 0.040), (0, 1, 0), mat,
                       hose_from=(x, by1 + 0.005, top + 0.060))
        # vedení od čela rámu po horní hraně pravé pásnice k zadní straně držáku
        ys = [c.base_y0 + 0.02, c.base_y0 - 0.25, c.base_y0 - 0.05, c.base_y0 - 0.35, y_conv + 0.08]
        pts = [(-0.26 + (x + 0.06) * 0.3, c.base_y0 + 0.02, c.deck_top - c.deck_plate - 0.20)]
        pts += [(-_drawbar_x(c, y) + (x + 0.06) * 0.25 + 0.01, y, z1 + 0.012) for y in ys[1:-1]]
        pts += [(x, ys[-1], z1 + 0.014), (x, by1 + 0.002, z - 0.03)]
        lines.append(P.sweep(f"{tag}_Line", P.hermite_path(pts, samples=8), 0.0065, "SDT_HoseBlack", segments=8))
    parts += lines
    for k, y in enumerate((c.base_y0 + 0.30, c.base_y0 - 0.15)):
        bx = -_drawbar_x(c, y)
        parts.append(box(f"Drawbar_LineClip{k}", bx - 0.035, bx + 0.035, y - 0.012, y + 0.012, z1, z1 + 0.026, steel))
    grp = empty("drawbarTractorSet", (0, 0, 0))
    _adopt(grp, parts + list(extra) + [bpy.data.objects[n] for n in ("airIn", "airOut", "airIn_detached", "airOut_detached")])
    return grp


def _max_car(c, y_conv, z1):
    """Varianta za auto / pickup (konfigurace CAR, skupina drawbarCarSet): kulová hlava s nájezdovou brzdou jako
    _car_coupler, rozměry vztažené ke spojce. Střed koule tažného zařízení = attacherJoint. Kabel 13pin je společný (_max_electric)."""
    by, bz = c.coupler_y, c.coupler_z
    az = bz + 0.027
    parts = []
    parts.append(P.loft_y("Coupler_Head", [
        (by - 0.062, 0.020, bz + 0.015, bz + 0.050, 2.5), (by - 0.050, 0.036, bz, bz + 0.066, 3.0),
        (by - 0.020, 0.046, bz - 0.008, bz + 0.074, 3.5), (by + 0.030, 0.046, bz - 0.008, bz + 0.076, 3.5),
        (by + 0.060, 0.040, bz, bz + 0.066, 3.0), (by + 0.080, 0.030, bz + 0.005, bz + 0.050, 2.5)], "SDT_CastIron"))
    parts.append(tube("Coupler_Handle", (0, by - 0.045, bz + 0.072), (0, by + 0.12, bz + 0.107), 0.011, "SDT_CastIron",
                      segments=10))
    parts.append(tube("Coupler_HandleGrip", (0, by + 0.10, bz + 0.103), (0, by + 0.165, bz + 0.116), 0.016, "SDT_PaintRed",
                      segments=12))
    parts.append(cylinder_x("Coupler_WearRing", (0.047, by + 0.005, bz + 0.042), 0.012, 0.008, "SDT_Plastic", segments=16))
    parts.append(cylinder_x("Coupler_WearIndicator", (0.052, by + 0.005, bz + 0.042), 0.008, 0.006, "SDT_LedGreen",
                            segments=12))
    hy1 = by + 0.67
    parts.append(tube("Coupler_DrawTube", (0, by + 0.07, az), (0, by + 0.25, az), 0.025, "SDT_Steel", segments=14))
    pleats = []
    y0, y1, n = by + 0.095, by + 0.185, 8
    for k in range(2 * n + 1):
        r = 0.031 if k % 2 == 0 else 0.042
        pleats.append((y0 + (y1 - y0) * k / (2 * n), r, az - r, az + r, 2.0))
    parts.append(P.loft_y("Coupler_Bellows", pleats, "SDT_Rubber", segments=18))
    parts.append(P.loft_y("Coupler_Housing", [
        (y1, 0.046, az - 0.050, az + 0.050, 6.0), (y1 + 0.02, 0.052, az - 0.055, az + 0.055, 6.0),
        (hy1 - 0.07, 0.052, az - 0.058, az + 0.058, 6.0), (hy1, 0.044, az - 0.040, az + 0.040, 5.0)], "SDT_Steel"))
    for side, sx in (("L", 1), ("R", -1)):
        parts.append(box(f"Coupler_Flange_{side}", sx * 0.050, sx * 0.058, by + 0.29, by + 0.59, az - 0.07, az + 0.06,
                         "SDT_Steel"))
        for k, fy in enumerate((by + 0.35, by + 0.53)):
            parts.append(cylinder_x(f"Coupler_Bolt_{side}{k}", (sx * 0.062, fy, az), 0.011, 0.01, "SDT_Steel", segments=6))
    top = az + 0.058
    px, py = 0.0, by + 0.50
    parts.append(box("Coupler_BrakePivot", px - 0.022, px + 0.022, py - 0.03, py + 0.03, top - 0.005, top + 0.03,
                     "SDT_Steel"))
    lever_end = Vector((px, by + 0.77, top + 0.19))
    parts.append(tube("Coupler_BrakeLever", (px, py, top + 0.02), lever_end, 0.013, "SDT_Frame", segments=10))
    grip_dir = (lever_end - Vector((px, py, top + 0.02))).normalized()
    parts.append(tube("Coupler_BrakeGrip", lever_end - grip_dir * 0.03, lever_end + grip_dir * 0.07, 0.019, "SDT_Rubber",
                      segments=12))
    lever_mid = Vector((px, py, top + 0.02)).lerp(lever_end, 0.4)
    spring_foot = Vector((0.03, by + 0.31, az + 0.035))
    parts.append(tube("Coupler_GasSpring", spring_foot, spring_foot.lerp(lever_mid, 0.6), 0.011, "SDT_Frame", segments=10))
    parts.append(tube("Coupler_GasSpringRod", spring_foot.lerp(lever_mid, 0.6), lever_mid, 0.005, "SDT_Steel", segments=8))
    # táhlo brzdy po horní straně příček (pod nimi by procházelo pásnicemi) k čelu rámu
    # podpěrné kolečko (objímka a trubka) stojí v ose oje: táhlo ho obejde obloukem nad objímkou a vedle trubky
    jy = c.jockey_y
    rod = [(0, hy1 + 0.005, az - 0.01), (0, y_conv + 0.25, z1 + 0.018), (0, jy - 0.20, z1 + 0.018), (0.08, jy - 0.12, bz + 0.13),
           (0.08, jy + 0.12, bz + 0.13), (0, jy + 0.20, z1 + 0.018), (0, c.base_y0 - 0.30, z1 + 0.018),
           (0, c.base_y0 - 0.02, c.deck_top - c.deck_plate - 0.12)]
    parts.append(P.sweep("Coupler_BrakeRod", P.hermite_path(rod, samples=8), 0.008, "SDT_Steel", segments=8))
    cable = P.hermite_path([(0.024, py + 0.02, top + 0.02), (0.06, by + 0.48, az + 0.04), (0.075, by + 0.33, az - 0.04),
                            (0.07, by + 0.18, bz - 0.07), (0.045, by + 0.07, bz - 0.095), (0.035, by + 0.045, bz - 0.10)],
                           samples=10)
    parts.append(P.sweep("Coupler_BreakawayCable", cable, 0.0035, "SDT_Steel", segments=6))
    end = cable[-1]
    ring = [end + Vector((0, 0.018 * math.sin(a), -0.018 - 0.028 * math.cos(a)))
            for a in (2 * math.pi * k / 16 for k in range(17))]
    parts.append(P.sweep("Coupler_Carabiner", ring, 0.0035, "SDT_Steel", segments=6))
    grp = empty("drawbarCarSet", (0, 0, 0))
    _adopt(grp, parts)
    return grp


def _max_electric(c, y_conv, z1):
    """Elektrická přípojka společná oběma variantám: kabel od zásuvky na čele rámu po levé pásnici k držáku na hlavě oje
    (uzel electric = začátek kabelu, který hra kreslí k tahači; electric_detached = zaparkovaná zástrčka v držáku)."""
    top = z1 + 0.012
    x = 0.090
    by0, by1 = y_conv - 0.035, y_conv - 0.015
    box("Drawbar_ElecBracket", x - 0.032, x + 0.032, by0, by1, top, top + 0.110, "SDT_Frame")
    box("Drawbar_ElecDock", 0.40, 0.46, c.base_y0 - 0.005, c.base_y0 + 0.001, c.deck_top - 0.16, c.deck_top - 0.08, "SDT_Plastic")
    z = top + 0.075
    tube("Drawbar_ElecSocket", (x, by0 - 0.026, z), (x, by1, z), 0.022, "SDT_Plastic", segments=14)
    tube("Drawbar_ElecSocketLid", (x, by0 - 0.032, z), (x, by0 - 0.026, z), 0.025, "SDT_ChargerGrey", segments=14)
    empty("electric", (x, by0 - 0.032, z))
    ys = [c.base_y0 - 0.25, c.base_y0 - 0.05, c.base_y0 - 0.35]
    pts = [(0.43, c.base_y0 + 0.001, c.deck_top - 0.12)] + [(_drawbar_x(c, y) - 0.012, y, z1 + 0.012) for y in ys]
    pts += [(x, y_conv + 0.08, z1 + 0.014), (x, by1 + 0.002, z - 0.03)]
    P.sweep("Drawbar_ElecCable", P.hermite_path(pts, samples=8), 0.006, "SDT_HoseBlack", segments=8)
    _coupling_head("electric_detached", (x, by1 + 0.095, top + 0.040), (0, 1, 0), "SDT_Plastic",
                   hose_from=(x, by1 + 0.005, top + 0.060))


def part_drawbar_max(base_y0, coupler_y, coupler_z, jockey_x, jockey_y, jockey_col, deck_top, deck_plate, ibeam_h,
                     root_x, tip_x, beam_w, beam_h, converge):
    """Pevná oj podle DPW 1800: dvě pásnice A-rámu z čela rámu, tři příčky, hlava (střed oka nebo koule = attacherJoint),
    podpěrné kolečko uprostřed (pohyblivá skupina jockeyWheel, kterou animace moveSupport zvedá). Spojka podle konfigurace
    v obchodě: tažné oko za traktor (drawbarTractorSet) nebo kulová hlava za auto (drawbarCarSet), elektrika je společná."""
    c = types.SimpleNamespace(base_y0=base_y0, coupler_y=coupler_y, coupler_z=coupler_z, jockey_y=jockey_y, deck_top=deck_top,
                              deck_plate=deck_plate, root_x=root_x, tip_x=tip_x, converge=converge)
    frame, steel = "SDT_Frame", "SDT_Steel"
    zb = deck_top - deck_plate
    z0, z1 = coupler_z - beam_h / 2, coupler_z + beam_h / 2
    y_root, y_conv = base_y0 + 0.05, coupler_y + converge
    for side, sx in (("L", 1), ("R", -1)):
        root = (sx * root_x, y_root)
        conv = (sx * tip_x, y_conv)
        _flat_beam(f"Drawbar_{side}", root, conv, beam_w, z0, z1, frame)
        box(f"DrawbarMount_{side}", sx * root_x - 0.10, sx * root_x + 0.10, base_y0 - 0.03, base_y0 + 0.55,
            z1, zb - ibeam_h + 0.03, frame)
        box(f"DrawbarGusset_{side}", sx * root_x - 0.012, sx * root_x + 0.012, base_y0 - 0.03,
            base_y0 + 0.80, z0 - 0.11, z0, frame)
        for k, dy in enumerate((0.07, 0.40)):
            cylinder_z(f"DrawbarBolt_{side}{k}", (sx * root_x, base_y0 + dy, zb - ibeam_h + 0.036), 0.016, 0.014, steel,
                       segments=6)
    for n, t in enumerate((0.31, 0.63, 0.95)):
        y = y_root + t * (y_conv - y_root)
        hx = _drawbar_x(c, y) - beam_w / 2 + 0.01
        _flat_beam(f"Drawbar_Cross{n}", (-hx, y), (hx, y), 0.06, coupler_z - 0.02, coupler_z + 0.02, frame)
    hy0, hy1 = coupler_y + 0.07, y_conv + 0.10
    _flat_beam("Drawbar_Head", (0, hy1), (0, hy0), 0.07, z0, z1, frame)
    # deska hlavy a šrouby jen u varianty za traktor (kulová hlava za auto má na tomtéž místě skříň nájezdové brzdy)
    head = [_flat_beam("Drawbar_HeadPlate", (0, y_conv + 0.14), (0, y_conv - 0.10), 0.26, z1, z1 + 0.012, frame)]
    for dy in (-0.05, 0.03):
        head.append(cylinder_z(f"Drawbar_HeadBolt{dy:+.2f}", (0, y_conv + dy, z1 + 0.012 + 0.007), 0.013, 0.014, steel,
                               segments=6))
    _max_tractor(c, y_conv, z0, z1, head)
    _max_car(c, y_conv, z1)
    _max_electric(c, y_conv, z1)

    jx, jy = jockey_x, jockey_y
    bx = _drawbar_x(c, jy)
    bz = coupler_z
    box("Jockey_Bridge", -bx, bx, jy - 0.05, jy + 0.05, bz - 0.025, bz + 0.025, frame)
    box("Jockey_Clamp", jx - 0.11, jx + 0.11, jy - 0.09, jy + 0.09, bz + 0.025, bz + 0.095, frame)
    moving = [
        tube("Jockey_Tube", (jx, jy, 0.30), (jx, jy, bz + 0.40), 0.045, steel, segments=14),
        tube("Jockey_Crank", (jx - 0.20, jy, bz + 0.40), (jx + 0.20, jy, bz + 0.40), 0.014, frame, segments=8),
        tube("Jockey_CrankGrip", (jx + 0.12, jy, bz + 0.40), (jx + 0.22, jy, bz + 0.40), 0.022, "SDT_Rubber", segments=10),
        box("Jockey_Fork", jx - 0.075, jx + 0.075, jy - 0.035, jy + 0.035, 0.12, 0.31, steel),
        cylinder_x("Jockey_Wheel", (jx, jy, 0.14), 0.14, 0.09, "SDT_Rubber", segments=24),
    ]
    pivot = empty("jockeyWheel", (jx, jy, coupler_z))
    _adopt(pivot, moving)
    _jockey_collision(pivot, jx, jy, jockey_col)
    aj = empty("attacherJoint", (0, coupler_y, coupler_z))
    aj.rotation_euler = (0, 0, math.radians(90))
    PL.localize((0, base_y0, 0))
