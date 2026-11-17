"""Kolize sklopného žebříku (Middle; Max po převzetí build_ladder) se zbytkem vleku ve všech fázích animace foldLadder (mesh-level,
ne bbox) a rozměry žebříku vůči obrysu vleku.

Žebřík je zavěšený nahoře z boku: složený leží vodorovně podél boku těsně pod horní deskou, rozložený visí svisle dolů z čepu
(ladderHinge, osa X kolmá na bok, 90°). Madla (ladderGrab, sourozenec kloubu, sklápí se opačně) míří rozložená nahoru nad desku.
Pohyblivé díly = děti ladderHinge a ladderGrab. Zkouší se mřížka poloh (žebřík u × madla v, 0..1 po 0,1, takže pokrývá i každé
časování obou kloubů, ne jen u == v) a to s nohami zasunutými i vysunutými o LEG_TRAVEL. Pro každou polohu se postaví BVH
pohyblivých dílů a ověří průnik s BVH ostatních viditelných dílů vleku (bez kolizních tvarů col*/triggerů). Hlásí se i nejmenší
vzdálenost pohyblivého dílu od pevného povrchu a spodek žebříku nad zemí. Dotek čepu s konzolou je konstrukční (ignoruje se).

    blender.exe -b blender\\spraydrone_trailer_middle.blend --python blender\\check_ladder.py -- middle
    blender.exe -b blender\\spraydrone_trailer_max.blend --python blender\\check_ladder.py -- max
"""
import os
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
which = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "middle"
p = os.path.join(HERE, f"build_trailer_{which}.py")
ns = {"__file__": p, "__name__": "check_ladder"}
exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
if "ladderHinge" not in bpy.data.objects or "ladderGrab" not in bpy.data.objects:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ns["build"]()
bpy.context.view_layer.update()

hinge = bpy.data.objects["ladderHinge"]
grab = bpy.data.objects["ladderGrab"]
moving = {o.name for o in hinge.children_recursive} | {o.name for o in grab.children_recursive}
SKIP = ("col", "fillTrigger", "exactFill", "concentrateFill", "dieselFill", "ladderTrigger")
IGNORE = {("LadderMount_Plate", "TopBeam_R"), ("Ladder_Pin", "LadderMount_Boss"), ("Ladder_Hub", "LadderMount_Boss")}
mine = set()
for cname in (ns["COLLECTION_NAME"], ns["PREVIEW_COLLECTION"]):
    if cname in bpy.data.collections:
        mine |= {o.name for o in bpy.data.collections[cname].all_objects}


def is_shape(o):
    return o.name.startswith(SKIP) or bool(o.get("i3D_nonRenderable"))


def world_mesh(o, dg):
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    verts = [o.matrix_world @ v.co for v in me.vertices]
    polys = [tuple(pl.vertices) for pl in me.polygons]
    ev.to_mesh_clear()
    return verts, polys


def combined_bvh(objs, dg):
    verts, polys, owner = [], [], []
    for o in objs:
        v, pl = world_mesh(o, dg)
        base = len(verts)
        verts += v
        for q in pl:
            polys.append(tuple(i + base for i in q))
            owner.append(o.name)
    return BVHTree.FromPolygons(verts, polys, epsilon=0.0), owner, verts


move_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.name in moving and not is_shape(o)]
static_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.name in mine and o.name not in moving
               and not is_shape(o) and not o.hide_render]
print(f"pohyblivych dilu: {len(move_objs)}, pevnych: {len(static_objs)}")

fold = ns["ladder_fold_angle"]()
fold_g = ns["ladder_grab_fold_angle"]()


def pose(u, v, leg=0.0):
    hinge.rotation_euler.x = fold * u
    grab.rotation_euler.x = fold_g * v
    bpy.context.view_layer.update()


def bbox(label, u, v):
    pose(u, v)
    dg = bpy.context.evaluated_depsgraph_get()
    for name, group in (("zebrik", [o for o in move_objs if o.name.split("_")[0] == "Ladder" and "Grab" not in o.name]),
                        ("madla", [o for o in move_objs if "Grab" in o.name])):
        pts = []
        for o in group:
            pts += world_mesh(o, dg)[0]
        mn = Vector((min(x.x for x in pts), min(x.y for x in pts), min(x.z for x in pts)))
        mx = Vector((max(x.x for x in pts), max(x.y for x in pts), max(x.z for x in pts)))
        print(f"BBOX {label:10s} {name:6s} x {mn.x:7.3f}..{mx.x:7.3f}  y {mn.y:7.3f}..{mx.y:7.3f}  z {mn.z:7.3f}..{mx.z:7.3f}")


hw = ns["TOP_W"] / 2
h = ns["ladder_geometry"]()[0]
print(f"obrys vleku: x +-{hw:.3f}, y ramu {ns['BASE_Y0']:.3f}..{ns['BASE_Y1']:.3f}, desky {ns['TOP_Y0']:.3f}..{ns['TOP_Y1']:.3f}; "
      f"cep ({h.x:.3f}, {h.y:.3f}, {h.z:.3f}), smer slozeni {ns['LADDER_FOLD_DIR']:+.0f}")
bbox("rozlozeny", 0.0, 0.0)
bbox("slozeny", 1.0, 1.0)

mount = [o for o in static_objs if o.name.startswith("LadderMount_")]
pose(0, 0)
dg = bpy.context.evaluated_depsgraph_get()
rest = [o for o in static_objs if o not in mount]
rest_bvh, rest_owner, _ = combined_bvh(rest, dg)
mt_bvh, mt_owner, _ = combined_bvh(mount, dg)
mt_pairs = sorted({(mt_owner[a], rest_owner[b]) for a, b in mt_bvh.overlap(rest_bvh)})
print("konzola zebriku x pevne dily:", mt_pairs if mt_pairs else "bez pruniku")

N = 10
total_bad = 0
worst = 1e9
seen = {}
for leg in (0.0,):
    pose(0, 0, leg)
    dg = bpy.context.evaluated_depsgraph_get()
    static_bvh, static_owner, _ = combined_bvh(static_objs, dg)
    bad = 0
    wl = 1e9
    for ku in range(N + 1):
        for kv in range(N + 1):
            u, v = ku / N, kv / N
            pose(u, v, leg)
            dg = bpy.context.evaluated_depsgraph_get()
            mv_bvh, mv_owner, mv_verts = combined_bvh(move_objs, dg)
            pairs = {(mv_owner[a], static_owner[b]) for a, b in mv_bvh.overlap(static_bvh)} - IGNORE
            if pairs:
                bad += 1
                for pr in pairs:
                    seen.setdefault(pr, []).append((leg, u, v))
            if ku == kv or (ku in (0, N) and kv in (0, N)):
                dmin, nearest = 1e9, ""
                for o in move_objs:
                    for vv in world_mesh(o, dg)[0]:
                        loc, nor, idx, d = static_bvh.find_nearest(vv, 0.5)
                        if d is not None and d < dmin:
                            dmin, nearest = d, f"{o.name} -> {static_owner[idx]}"
                wl = min(wl, dmin)
                if ku == kv:
                    zmin = min(x.z for x in mv_verts)
                    print(f"noha {leg:.2f} u=v={u:4.2f} {'KOLIZE' if pairs else 'ok':6s} min.vzdalenost {dmin:6.3f} m ({nearest}) zmin {zmin:6.3f}")
    total_bad += bad
    worst = min(worst, wl)
    print(f"noha {leg:.2f}: poloh s kolizi {bad} z {(N + 1) ** 2}, nejmensi vzdalenost na diagonale {wl:.3f} m")
for pr, where in sorted(seen.items()):
    print("PRUNIK", pr, "poloh", len(where), "napr.", where[:3])
print("VYSLEDEK:", f"KOLIZE v {total_bad} polohach" if total_bad else "bez kolize ve vsech polohach",
      f"| nejmensi vzdalenost {worst:.3f} m")
