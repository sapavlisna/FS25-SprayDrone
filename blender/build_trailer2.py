"""Nová verze přívěsu podle referenčního videa (nuWay Ag, 22ft deckover).

Staví se PARALELNĚ vedle původního `build_trailer.py` (jiná kolekce, posazeno stranou),
aby šlo oba modely v Blenderu porovnat. Fáze 1: rám, náprava, kola, rezerva.
Viz docs/PLAN-prives-remodel.md.
"""

import bpy
import bmesh
import math
import mathutils

COLLECTION_NAME = "SprayDroneTrailer_V2"
OFFSET_Y = 0.0  # starý model smazán, nový je teď na středu scény

# --- Parametry (m), viz reference/frames_hq ---
DECK_LEN = 6.7       # 22 ft deckover
DECK_WIDTH = 2.03    # ~80 in, typicka sirka deckover valniku
DECK_THICK = 0.05

WHEEL_RADIUS = 0.42  # 16-ply, prakticky stejne jako u puvodniho modelu
WHEEL_WIDTH = 0.3
AXLE_CENTER_X = -DECK_LEN / 2 + 1.5   # tandem blizko zadni casti ramu
AXLE_SPACING = 2 * WHEEL_RADIUS + 0.18
AXLE_X = [AXLE_CENTER_X - AXLE_SPACING / 2, AXLE_CENTER_X + AXLE_SPACING / 2]
TRACK_Y = DECK_WIDTH / 2 + WHEEL_WIDTH / 2 - 0.02  # kola u deckoveru cnici mimo hranu paluby

RAIL_HEIGHT = 0.22
FRAME_TOP_Z = WHEEL_RADIUS + 0.16   # vyska hrany ramu nad zemi (nizky deckover)
DECK_TOP_Z = FRAME_TOP_Z + DECK_THICK

TONGUE_LEN = 1.7
HITCH_Z = 0.55


def clear_collection():
    if COLLECTION_NAME in bpy.data.collections:
        coll = bpy.data.collections[COLLECTION_NAME]
        for obj in list(coll.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
    else:
        coll = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(coll)
    return coll


def add_box(coll, name, dims, loc, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(loc[0], loc[1] + OFFSET_Y, loc[2]))
    obj = bpy.context.active_object
    obj.name = name
    obj.dimensions = dims
    obj.rotation_euler = rot
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


def add_cylinder(coll, name, radius, depth, loc, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, vertices=verts, location=(loc[0], loc[1] + OFFSET_Y, loc[2])
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rot
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


MATERIALS = {
    "Steel_Dark": ((0.05, 0.05, 0.06), 0.85, 0.5),
    "Steel_Galvanized": ((0.62, 0.64, 0.66), 0.85, 0.35),
    "Deck_Plate": ((0.22, 0.22, 0.23), 0.75, 0.55),
    "Rubber": ((0.02, 0.02, 0.02), 0.0, 0.85),
    "Paint_Green": ((0.05, 0.16, 0.07), 0.2, 0.4),
    "Paint_Orange": ((0.85, 0.32, 0.03), 0.1, 0.4),
    "Plastic_White": ((0.83, 0.84, 0.81), 0.0, 0.35),
    "Plastic_Clear": ((0.75, 0.8, 0.78), 0.0, 0.15),
    "Plastic_Blue": ((0.05, 0.25, 0.55), 0.05, 0.35),
    "Lamp_Red": ((0.55, 0.02, 0.02), 0.0, 0.2),
    "Lamp_Amber": ((0.6, 0.32, 0.02), 0.0, 0.2),
}


def get_material(name):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    color, metallic, roughness = MATERIALS[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = (*color, 1.0)
    return mat


MATERIAL_RULES = [
    (("Wheel_",), "Rubber"),
    (("HubCap_",), "Steel_Galvanized"),
    (("Lamp_Red",), "Lamp_Red"),
    (("Lamp_Amber",), "Lamp_Amber"),
    (("Gusset_",), "Paint_Green"),
    (("FrontRail_Mesh",), "Steel_Galvanized"),
    (("FrontRail_", "Stair_"), "Steel_Dark"),
    (("Tank_Water",), "Plastic_Clear"),
    (("Tank_Induction_Strap",), "Steel_Dark"),
    (("Tank_",), "Plastic_White"),
    (("TankLeg_",), "Steel_Dark"),
    (("Manifold_Handle",), "Plastic_Blue"),
    (("Manifold_",), "Steel_Galvanized"),
    (("HoseReel_",), "Steel_Galvanized"),
    (("_Hood",), "Paint_Orange"),
    (("Gen_", "Toolbox", "SecurityBox_"), "Steel_Dark"),
    (("JackLeg_",), "Steel_Galvanized"),
    (("WorkLight",), "Plastic_White"),
    (("FlightDeck",), "Deck_Plate"),
    (("Deck",), "Deck_Plate"),
]


def apply_materials(coll):
    for obj in coll.objects:
        if obj.type != 'MESH':
            continue
        mat_name = "Steel_Dark"
        for fragments, candidate in MATERIAL_RULES:
            if any(f in obj.name for f in fragments):
                mat_name = candidate
                break
        obj.data.materials.clear()
        obj.data.materials.append(get_material(mat_name))


def build_frame(coll):
    rail_z = FRAME_TOP_Z - RAIL_HEIGHT / 2
    for side, sy in (("L", 1), ("R", -1)):
        add_box(
            coll, f"MainRail_{side}", (DECK_LEN, 0.09, RAIL_HEIGHT),
            (0, sy * (DECK_WIDTH / 2 - 0.06), rail_z),
        )
    # pricne travesy pod palubou
    n_cross = 9
    for i in range(n_cross):
        x = -DECK_LEN / 2 + DECK_LEN * i / (n_cross - 1)
        add_box(coll, f"CrossMember_{i}", (0.07, DECK_WIDTH - 0.1, RAIL_HEIGHT - 0.04), (x, 0, rail_z))

    add_box(coll, "Deck", (DECK_LEN, DECK_WIDTH, DECK_THICK), (0, 0, DECK_TOP_Z - DECK_THICK / 2))

    # diamantovy okraj paluby (nastupni hrana) - tenky pruh po obvodu, jen vizualne odlisny material pozdeji
    add_box(coll, "DeckEdge_Rear", (0.04, DECK_WIDTH, DECK_THICK + 0.01), (-DECK_LEN / 2, 0, DECK_TOP_Z - DECK_THICK / 2))
    add_box(coll, "DeckEdge_Front", (0.04, DECK_WIDTH, DECK_THICK + 0.01), (DECK_LEN / 2, 0, DECK_TOP_Z - DECK_THICK / 2))

    # Oj - jeden rovny stredovy nosnik k oku zavesu (podle reference, ne V-tvar)
    tongue_tip_x = DECK_LEN / 2 + TONGUE_LEN
    drop = rail_z - HITCH_Z
    angle_y = math.atan2(drop, TONGUE_LEN)
    beam_len = math.hypot(TONGUE_LEN, drop)
    add_box(
        coll, "Tongue", (beam_len, 0.14, 0.12),
        ((DECK_LEN / 2 + tongue_tip_x) / 2, 0, (rail_z + HITCH_Z) / 2),
        rot=(0, angle_y, 0),
    )
    add_cylinder(
        coll, "HitchCoupler", 0.07, 0.22, (tongue_tip_x - 0.05, 0, HITCH_Z), rot=(math.radians(90), 0, 0),
    )


def build_axles(coll):
    HUB_RADIUS = 0.15
    HUB_DEPTH = 0.045
    for i, ax_x in enumerate(AXLE_X, start=1):
        add_cylinder(coll, f"Axle_{i}", 0.055, 2 * TRACK_Y - WHEEL_WIDTH, (ax_x, 0, WHEEL_RADIUS), rot=(math.radians(90), 0, 0))
        for side, sy in (("L", 1), ("R", -1)):
            add_cylinder(
                coll, f"Wheel_{i}{side}", WHEEL_RADIUS, WHEEL_WIDTH,
                (ax_x, sy * TRACK_Y, WHEEL_RADIUS), rot=(math.radians(90), 0, 0),
            )
            add_cylinder(
                coll, f"HubCap_{i}{side}", HUB_RADIUS, HUB_DEPTH,
                (ax_x, sy * (TRACK_Y + WHEEL_WIDTH / 2), WHEEL_RADIUS), rot=(math.radians(90), 0, 0),
            )
        # listove pero + tremeny (jednoducha tandemova zaves, bez vahadla)
        for side, sy in (("L", 1), ("R", -1)):
            y = sy * TRACK_Y
            add_box(coll, f"Leaf_{i}{side}", (0.55, 0.09, 0.05), (ax_x, y, WHEEL_RADIUS + 0.09))
            add_box(
                coll, f"UBolt_{i}{side}", (0.08, 0.11, FRAME_TOP_Z - RAIL_HEIGHT - WHEEL_RADIUS + 0.02),
                (ax_x, y, (FRAME_TOP_Z - RAIL_HEIGHT + WHEEL_RADIUS + 0.09) / 2),
            )
    # hanger konzoly z ramu k listovym perum, na kraji rozteze tandemu
    for hx in AXLE_X:
        for side, sy in (("L", 1), ("R", -1)):
            add_box(
                coll, f"Hanger_{hx:.1f}_{side}", (0.07, 0.08, FRAME_TOP_Z - RAIL_HEIGHT - WHEEL_RADIUS - 0.05),
                (hx, sy * TRACK_Y, (FRAME_TOP_Z - RAIL_HEIGHT + WHEEL_RADIUS + 0.05) / 2),
            )
    # rovnovazny nosnik (equalizer) mezi tremeny tandemu
    eq_x = (AXLE_X[0] + AXLE_X[1]) / 2
    for side, sy in (("L", 1), ("R", -1)):
        add_box(coll, f"Equalizer_{side}", (AXLE_SPACING + 0.15, 0.06, 0.09), (eq_x, sy * TRACK_Y, WHEEL_RADIUS + 0.09))


PLATFORM_LEN = DECK_LEN + 0.4   # strecha mirne preteka pres ram na obou koncich
PLATFORM_WIDTH = DECK_WIDTH + 0.08  # sloupky maji sedet na hrane ramu, ne viset mimo nej
PLATFORM_THICK = 0.08
STRUT_H = 1.95  # svetlost pod strechou, aby se pod ni dalo stat
PLATFORM_Z = DECK_TOP_Z + STRUT_H


def add_gusset(coll, name, post_x, sy, post_top_z):
    """Trojuhelnikova vzpera mezi sloupkem a hranou strechy (roh, jak na referenci)."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    size = 0.55
    thick = 0.02
    v0 = bm.verts.new((0, 0, 0))
    v1 = bm.verts.new((size, 0, 0))
    v2 = bm.verts.new((0, 0, size))
    v0b = bm.verts.new((0, thick, 0))
    v1b = bm.verts.new((size, thick, 0))
    v2b = bm.verts.new((0, thick, size))
    bm.faces.new((v0, v1, v2))
    bm.faces.new((v0b, v2b, v1b))
    bm.faces.new((v0, v2, v2b, v0b))
    bm.faces.new((v1, v0, v0b, v1b))
    bm.faces.new((v2, v1, v1b, v2b))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = (post_x - size, (sy * (PLATFORM_WIDTH / 2 - thick) if sy > 0 else sy * PLATFORM_WIDTH / 2) + OFFSET_Y, post_top_z - size)
    if sy < 0:
        obj.scale = (1, -1, 1)
    coll.objects.link(obj)
    return obj


def build_posts_and_deck(coll):
    n_posts = 4
    span = PLATFORM_LEN - 0.6
    post_xs = [-PLATFORM_LEN / 2 + 0.3 + span * i / (n_posts - 1) for i in range(n_posts)]
    side_ys = (PLATFORM_WIDTH / 2 - 0.06, -(PLATFORM_WIDTH / 2 - 0.06))

    for sy in side_ys:
        for sx in post_xs:
            add_box(coll, f"Post_{sx:.2f}_{sy:.2f}", (0.1, 0.1, STRUT_H), (sx, sy, DECK_TOP_Z + STRUT_H / 2))
            add_gusset(coll, f"Gusset_{sx:.2f}_{sy:.2f}", sx, 1 if sy > 0 else -1, DECK_TOP_Z + STRUT_H)

    add_box(coll, "FlightDeck", (PLATFORM_LEN, PLATFORM_WIDTH, PLATFORM_THICK), (0, 0, PLATFORM_Z))
    # zvyrazneny okraj strechy (rim) po obvodu - tenky lem, jak je videt na referenci
    add_box(coll, "FlightDeck_RimF", (0.03, PLATFORM_WIDTH, 0.05), (PLATFORM_LEN / 2, 0, PLATFORM_Z + PLATFORM_THICK / 2))
    add_box(coll, "FlightDeck_RimB", (0.03, PLATFORM_WIDTH, 0.05), (-PLATFORM_LEN / 2, 0, PLATFORM_Z + PLATFORM_THICK / 2))
    for sy in side_ys:
        add_box(coll, f"FlightDeck_Rim_{sy:.2f}", (PLATFORM_LEN, 0.03, 0.05), (0, sy, PLATFORM_Z + PLATFORM_THICK / 2))
    # zebra na spodni strane strechy (purliny), jak je videt na zaberu zdola
    n_ribs = 9
    for i in range(n_ribs):
        x = -PLATFORM_LEN / 2 + PLATFORM_LEN * i / (n_ribs - 1)
        add_box(coll, f"FlightDeck_Rib_{i}", (0.05, PLATFORM_WIDTH - 0.1, 0.07), (x, 0, PLATFORM_Z - PLATFORM_THICK / 2 - 0.035))


def build_front_platform_rail(coll):
    """Cela plocha strechy (FlightDeck) je pochozi - vpredu je jen zabradlo/sit po obvodu
    (nic pred ni neni), takze to vypada jako samostatna 'pilotni' plosina - presne jak na
    referencnim zaberu (ne uzky vyclenujici box)."""
    depth = 1.1  # jak hluboko od predni hrany strechy sahá zabradli
    front_x = PLATFORM_LEN / 2
    rail_h = 0.85
    top_z = PLATFORM_Z + PLATFORM_THICK / 2
    rail_z = top_z + rail_h / 2

    add_box(coll, "FrontRail_Front", (0.03, PLATFORM_WIDTH, rail_h), (front_x, 0, rail_z))
    add_box(coll, "FrontRail_MidBar", (0.03, PLATFORM_WIDTH, 0.03), (front_x, 0, top_z + rail_h * 0.55))
    for sy in (PLATFORM_WIDTH / 2 - 0.02, -(PLATFORM_WIDTH / 2 - 0.02)):
        add_box(coll, f"FrontRail_Side_{sy:.2f}", (depth, 0.03, rail_h), (front_x - depth / 2, sy, rail_z))
        add_box(coll, f"FrontRail_SideMid_{sy:.2f}", (depth, 0.03, 0.03), (front_x - depth / 2, sy, top_z + rail_h * 0.55))
    # sitova vypln v prednim rohu (pilot protection wall), jak je videt na zaberu
    add_box(coll, "FrontRail_Mesh", (0.015, PLATFORM_WIDTH - 0.1, rail_h - 0.12), (front_x - 0.01, 0, rail_z))


def build_front_stairs(coll):
    """Strme schodiste se schodnicemi a rovnymi stupni (ne zebrik s prickami), mimo pudorys
    paluby (na vnejsi strane, za sirkou platformy) - presne jak na referencnich zaberech."""
    width = 0.5
    y_center = PLATFORM_WIDTH / 2 + width / 2 + 0.03
    top_x = PLATFORM_LEN / 2 - 0.15
    top_z = PLATFORM_Z + PLATFORM_THICK / 2
    bottom_z = DECK_TOP_Z
    total_rise = top_z - bottom_z

    step_rise = 0.26
    step_run = 0.15  # strme schodiste (~60 stupnu), ne pozvolne
    n_steps = max(4, round(total_rise / step_rise))
    step_rise = total_rise / n_steps
    total_run = step_run * n_steps
    bottom_x = top_x - total_run

    stringer_len = math.hypot(total_run, total_rise)
    angle = math.atan2(total_rise, total_run)
    for side, sy in (("L", 1), ("R", -1)):
        y = y_center + sy * width / 2
        add_box(
            coll, f"Stair_Stringer_{side}", (stringer_len, 0.04, 0.12),
            ((top_x + bottom_x) / 2, y, (bottom_z + top_z) / 2 - 0.08), rot=(0, -angle, 0),
        )
    for i in range(n_steps):
        t = (i + 1) / n_steps
        step_x = bottom_x + total_run * t
        step_z = bottom_z + total_rise * t
        add_box(coll, f"Stair_Tread_{i}", (step_run + 0.03, width, 0.035), (step_x - step_run / 2, y_center, step_z))

    rail_h = 0.55
    for i in range(n_steps + 1):
        t = i / n_steps
        x = bottom_x + total_run * t
        z = bottom_z + total_rise * t
        add_cylinder(
            coll, f"Stair_RailPost_{i}", 0.016, rail_h, (x, y_center + width / 2 + 0.03, z + rail_h / 2), verts=8,
        )


def add_capsule_x(coll, name, radius, cyl_len, base_z, segments=16, cap_rings=4):
    """Kapslovita nadrz (valec + polokulove konce) s osou podel X - hlavni nadrz na referencich
    je zaobleny elipsoidni tvar, ne kuzelove dno."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    stations = [(-cyl_len / 2 - radius, 0.0)]
    for i in range(cap_rings, 0, -1):
        theta = (math.pi / 2) * i / cap_rings
        stations.append((-cyl_len / 2 - radius * math.cos(theta), radius * math.sin(theta)))
    stations.append((-cyl_len / 2, radius))
    stations.append((cyl_len / 2, radius))
    for i in range(1, cap_rings + 1):
        theta = (math.pi / 2) * i / cap_rings
        stations.append((cyl_len / 2 + radius * math.cos(theta), radius * math.sin(theta)))
    stations.append((cyl_len / 2 + radius, 0.0))

    rings = []
    for x, r in stations:
        if r < 1e-6:
            rings.append(None)
        else:
            rings.append([
                bm.verts.new((x, r * math.cos(2 * math.pi * k / segments), r * math.sin(2 * math.pi * k / segments)))
                for k in range(segments)
            ])

    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        if a is None:
            pole = bm.verts.new((stations[i][0], 0, 0))
            for k in range(segments):
                bm.faces.new((pole, b[k], b[(k + 1) % segments]))
        elif b is None:
            pole = bm.verts.new((stations[i + 1][0], 0, 0))
            for k in range(segments):
                bm.faces.new((pole, a[(k + 1) % segments], a[k]))
        else:
            for k in range(segments):
                k2 = (k + 1) % segments
                bm.faces.new((a[k], a[k2], b[k2], b[k]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = (0, 0, base_z + radius)
    coll.objects.link(obj)
    return obj


def build_tanks(coll):
    """Nadrze a manifold na nizke palube - 1000gal hlavni (kapslovity tvar), 175gal indukcni
    tote (hranata s popruhy) a 50gal cira na vodu, podle oficialnich specifikaci nuWayAg."""
    # 1000gal hlavni nadrz - velky kapslovity valec podel X, na ose vleku
    main_r, main_len = 0.5, 1.6
    main_x, main_y = -0.1, 0.0
    main = add_capsule_x(coll, "Tank_Main", main_r, main_len, DECK_TOP_Z)
    main.location = (main_x, main_y + OFFSET_Y, DECK_TOP_Z + main_r)

    # 175gal indukcni tote - hranata nadoba s cernymi popruhy, mezi hlavni nadrzi a generatory
    ind_dims = (0.7, 0.7, 0.85)
    ind_x, ind_y = -1.7, 0.5
    add_box(coll, "Tank_Induction", ind_dims, (ind_x, ind_y, DECK_TOP_Z + ind_dims[2] / 2))
    for frac in (0.3, 0.7):
        add_box(
            coll, f"Tank_Induction_Strap_{frac}", (ind_dims[0] + 0.03, ind_dims[1] + 0.03, 0.06),
            (ind_x, ind_y, DECK_TOP_Z + ind_dims[2] * frac),
        )

    # 50gal cira nadrz na vodu - mala kapsle, vpredu mimo bezpecnostni box
    water_r, water_len = 0.28, 0.35
    water_x, water_y = 1.7, 0.55
    water = add_capsule_x(coll, "Tank_Water", water_r, water_len, DECK_TOP_Z)
    water.location = (water_x, water_y + OFFSET_Y, DECK_TOP_Z + water_r)

    # stojanky pod nadrzemi (jen pod kapslovitymi, tote stoji rovnou na palube)
    for name, (tx, ty), r in (("Main", (main_x, main_y), main_r), ("Water", (water_x, water_y), water_r)):
        for fx, fy in ((r * 0.6, r * 0.35), (r * 0.6, -r * 0.35), (-r * 0.6, r * 0.35), (-r * 0.6, -r * 0.35)):
            add_box(coll, f"TankLeg_{name}_{fx:.2f}_{fy:.2f}", (0.04, 0.04, DECK_TOP_Z - 0.001),
                    (tx + fx, ty + fy, DECK_TOP_Z / 2))

    # manifold - rada uzaviracich ventilu na celni strane hlavni nadrze
    manifold_x = main_x - main_len / 2 - main_r - 0.06
    manifold_z = DECK_TOP_Z + 0.15
    for i in range(4):
        vy = main_y - 0.24 + i * 0.16
        add_cylinder(coll, f"Manifold_Valve_{i}", 0.035, 0.09, (manifold_x, vy, manifold_z),
                     rot=(0, math.radians(90), 0), verts=12)
        add_cylinder(coll, f"Manifold_Handle_{i}", 0.055, 0.02, (manifold_x - 0.05, vy, manifold_z),
                     rot=(0, math.radians(90), 0), verts=12)
    add_cylinder(coll, "Manifold_Pipe", 0.03, 0.7, (manifold_x, main_y, manifold_z - 0.14),
                 rot=(math.radians(90), 0, 0), verts=12)

    # hadicove navijaky na dvou blizkych sloupcich stresky
    for i, post_x in enumerate((0.2, 1.8)):
        reel_y = PLATFORM_WIDTH / 2 - 0.06
        reel_z = DECK_TOP_Z + STRUT_H - 0.5
        add_cylinder(coll, f"HoseReel_{i}", 0.16, 0.1, (post_x, reel_y - 0.1, reel_z),
                     rot=(math.radians(90), 0, 0), verts=16)
        add_cylinder(coll, f"HoseReel_Hub_{i}", 0.05, 0.12, (post_x, reel_y - 0.1, reel_z),
                     rot=(math.radians(90), 0, 0), verts=10)


def build_generators(coll):
    """Dva elektrocentraly (Predator/Duromax) vzadu na nizke palube, vedle sebe pres uzkou uzicku."""
    gen_dims = (0.75, 0.55, 0.62)
    gx, gy, gz = gen_dims
    # oba vedle sebe podel X, na strane y<0 - mimo pudorys schodu (ty jsou pri y in [-0.03, 0.53])
    positions = ((-2.7, -0.35), (-1.9, -0.35))
    for i, (gen_x, gy_pos) in enumerate(positions):
        base_z = DECK_TOP_Z
        center_z = base_z + gz / 2
        add_box(coll, f"Gen_{i}_Frame", gen_dims, (gen_x, gy_pos, center_z))
        hood = (gx - 0.1, gy - 0.06, gz - 0.14)
        add_box(coll, f"Gen_{i}_Hood", hood, (gen_x, gy_pos, base_z + 0.05 + hood[2] / 2))
        add_box(coll, f"Gen_{i}_Panel", (0.3, 0.03, 0.2), (gen_x, gy_pos - gy / 2 - 0.02, center_z))
        add_cylinder(coll, f"Gen_{i}_FuelCap", 0.05, 0.03, (gen_x + gx / 2 - 0.12, gy_pos, base_z + gz - 0.02), verts=12)


def build_toolbox(coll):
    """Uzamykatelny toolbox pod ramem u oje (diamantovy plech, jak na referenci)."""
    dims = (0.55, 0.4, 0.28)
    x = DECK_LEN / 2 - 0.5
    z = FRAME_TOP_Z - RAIL_HEIGHT / 2
    add_box(coll, "Toolbox", dims, (x, DECK_WIDTH / 2 - dims[1] / 2 - 0.05, z))
    add_box(coll, "Toolbox_Latch", (0.06, 0.03, 0.06), (x - dims[0] / 2 + 0.05, DECK_WIDTH / 2 - dims[1] + 0.02, z))


def build_drone_security_box(coll):
    """Uzamykatelny box na dron - diamantovy plech, vyklopne viko, na palube vpredu."""
    dims = (1.3, 0.75, 0.45)
    x = 1.7
    y = -0.55
    z = DECK_TOP_Z + dims[2] / 2
    add_box(coll, "SecurityBox_Body", dims, (x, y, z))
    lid = add_box(coll, "SecurityBox_Lid", (dims[0], dims[1], 0.04), (x, y - dims[1] / 2, z + dims[2] / 2 + 0.02))
    lid.rotation_euler = (math.radians(-35), 0, 0)
    add_box(coll, "SecurityBox_Lock", (0.05, 0.05, 0.06), (x + dims[0] / 2 - 0.1, y + dims[1] / 2, z + dims[2] / 2))


def build_lights(coll):
    for side, sy in (("L", 1), ("R", -1)):
        add_box(coll, f"Lamp_Red_{side}", (0.03, 0.09, 0.14), (-DECK_LEN / 2 + 0.06, sy * (DECK_WIDTH / 2 - 0.1), DECK_TOP_Z + 0.1))
        add_box(coll, f"Lamp_Amber_{side}", (0.03, 0.09, 0.06), (0, sy * (DECK_WIDTH / 2 - 0.02), DECK_TOP_Z + 0.03))
    # pracovni svetlo pod strechou vzadu (svitilo pri praci za tmy na referencich)
    add_box(coll, "WorkLight", (0.14, 0.08, 0.06), (-PLATFORM_LEN / 2 + 0.3, 0, PLATFORM_Z - PLATFORM_THICK / 2 - 0.05))


def build_stabilizer_legs(coll):
    """Jednoduchy hydraulicky zvedak vpredu u oje + 2 rohove vyrovnavaci nohy vzadu - vysunute az na zem."""
    frame_bottom = FRAME_TOP_Z - RAIL_HEIGHT
    foot_h = 0.03
    add_cylinder(coll, "JackLeg_Front", 0.05, HITCH_Z - foot_h, (DECK_LEN / 2 + 0.3, 0, (HITCH_Z + foot_h) / 2), verts=10)
    add_box(coll, "JackLeg_FrontFoot", (0.14, 0.14, foot_h), (DECK_LEN / 2 + 0.3, 0, foot_h / 2))
    for side, sy in (("L", 1), ("R", -1)):
        x = -DECK_LEN / 2 + 0.35
        y = sy * (DECK_WIDTH / 2 - 0.1)
        add_cylinder(coll, f"JackLeg_Rear_{side}", 0.045, frame_bottom - foot_h, (x, y, (frame_bottom + foot_h) / 2), verts=10)
        add_box(coll, f"JackLeg_RearFoot_{side}", (0.12, 0.12, foot_h), (x, y, foot_h / 2))


def build_drones_on_deck():
    """Napoji existujici drony (build_drone.py, beze zmeny) NA STRECHU (tam se lita, pristupne
    z cellni plosiny po zebriku) - ne na nizkou palubu, kde jsou nadrze/generatory."""
    import build_drone
    import importlib
    importlib.reload(build_drone)
    coll = build_drone.clear_collection()
    z = PLATFORM_Z + PLATFORM_THICK / 2 + 0.015
    build_drone.build_drone(
        coll, name="Drone_A", origin=(0.8, 0.35 + OFFSET_Y, z), accent="Drone_Accent_A", arms_folded=1.0,
    )
    build_drone.build_drone(
        coll, name="Drone_B", origin=(-1.2, -0.35 + OFFSET_Y, z), accent="Drone_Accent_B", arms_folded=1.0,
    )
    bpy.context.view_layer.update()
    print(f"Drones on V2 roof: {len(coll.objects)} objects")


def build():
    coll = clear_collection()
    build_frame(coll)
    build_axles(coll)
    build_posts_and_deck(coll)
    build_front_platform_rail(coll)
    build_front_stairs(coll)
    build_tanks(coll)
    build_generators(coll)
    build_toolbox(coll)
    build_drone_security_box(coll)
    build_lights(coll)
    build_stabilizer_legs(coll)
    apply_materials(coll)
    bpy.context.view_layer.update()
    print(f"Trailer V2 fáze 1 built: {len(coll.objects)} objects in '{COLLECTION_NAME}'")


if __name__ == "__main__":
    build()
