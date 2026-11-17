"""Hrany paluby vleků: kovové lemy (výchozí, vznikají ve skriptu vleku jako Rail_*, FrontBeam*, RearBeam) nebo dřevěné desky s kovovými
pásy a šrouby. Obě varianty jsou v modelu zároveň, každá ve své skupině (deckEdgeSteel, deckEdgeWood); v i3d je dřevěná skrytá
a konfigurace Hrany paluby v obchodě (sprayDroneDeckEdge) přepíná viditelnost objectChange.

    build_deck_edges(deck_top)    - zabalí kovové lemy do deckEdgeSteel a ke každému postaví dřevěnou náhradu v deckEdgeWood
    part_wood_edge(...)           - jedna dřevěná hrana jako díl knihovny
"""

import math

import bpy
from mathutils import Matrix, Vector

import parts_lib as PL
import sdt_parts as P

box, cylinder_x = P.box, P.cylinder_x

# jména kovových lemů ve skriptech vleků; vezmou se jen ty, které existují a sahají k horní ploše paluby (Middle má pod deskou
# ještě vnitřní FrontBeam, ten hranou není)
EDGE_NAMES = ("Rail_L", "Rail_R", "RailFront_L", "RailFront_R", "FrontBeam", "FrontBeamOuter", "RearBeam")
PLANK_H = 0.06                 # výška jedné desky; počet desek v hraně se zaokrouhlí a desky se rozdělí rovnoměrně
PLANK_GAP = 0.004              # spára mezi deskami nad sebou i na stycích
MAX_PIECE = 4.0                # delší hrana je z více kusů, spáry se střídají
STRAP_PITCH = 0.9              # rozteč kovových pásů


def _bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def part_wood_edge(length, height, thickness):
    """Jedna dřevěná hrana paluby: desky nad sebou (delší hrana z více kusů se střídavými spárami), na vnější straně kovové pásy
    s hlavou přes horní hranu a dvojicí šroubů. Lokální počátek: vnější líc hrany je rovina x = 0 (dřevo leží v x -thickness..0,
    pásy o 8 mm vně), délka je podél Y se středem v y = 0, spodek hrany je v z = 0."""
    n = max(1, round((height + PLANK_GAP) / (PLANK_H + PLANK_GAP)))
    ph = (height - (n - 1) * PLANK_GAP) / n
    pieces = max(1, math.ceil(length / MAX_PIECE))
    y_lo = -length / 2
    for k in range(n):
        z0 = k * (ph + PLANK_GAP)
        step = length / pieces
        shift = step * 0.5 if k % 2 else 0.0
        cuts = [y_lo] + [y_lo + step * i + shift for i in range(1, pieces)] + [y_lo + length]
        for j in range(len(cuts) - 1):
            a = cuts[j] + (PLANK_GAP / 2 if j else 0.0)
            b = cuts[j + 1] - (PLANK_GAP / 2 if j < len(cuts) - 2 else 0.0)
            box(f"EdgeBoard_{k}_{j}", -thickness, 0.0, a, b, z0, z0 + ph, "SDT_DeckWood")
    count = max(2, round(length / STRAP_PITCH) + 1)
    inset = 0.07
    for i in range(count):
        y = y_lo + inset + (length - 2 * inset) * i / (count - 1)
        w = 0.025
        box(f"EdgeStrap_{i}", 0.0, 0.008, y - w, y + w, 0.0, height + 0.008, "SDT_Steel")
        box(f"EdgeStrapCap_{i}", -thickness, 0.008, y - w, y + w, height, height + 0.008, "SDT_Steel")
        for m, zf in enumerate((0.3, 0.7)):
            cylinder_x(f"EdgeBolt_{i}_{m}", (0.011, y, height * zf), 0.009, 0.006, "SDT_Steel", segments=6)


def _adopt(parent, objs):
    for o in objs:
        w = o.matrix_world.copy()
        o.parent = parent
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_world = w


def build_deck_edges(deck_top):
    """Zabalí kovové lemy do skupiny deckEdgeSteel a ke každému postaví dřevěnou náhradu stejných rozměrů ve skupině deckEdgeWood
    (obě skupiny leží pod kořenem vleku, dřevěná se skrývá při exportu). Příčné hrany se zkrátí o tloušťku bočních, ať se desky
    v rozích nepřekrývají."""
    found = []
    for name in EDGE_NAMES:
        o = bpy.data.objects.get(name)
        if o is None or o.type != "MESH":
            continue
        lo, hi = _bbox(o)
        if hi.z < deck_top - 0.02:
            continue
        found.append((o, lo, hi))
    if not found:
        return
    sides = [(o, lo, hi) for o, lo, hi in found if hi.y - lo.y >= hi.x - lo.x]
    side_names = {o.name for o, _, _ in sides}
    side_t = max((hi.x - lo.x for _, lo, hi in sides), default=0.0)
    x_max = max((hi.x for _, _, hi in sides), default=None)
    y_mid = sum((lo.y + hi.y) / 2 for _, lo, hi in found) / len(found)
    steel = P.empty("deckEdgeSteel", (0, 0, 0))
    wood = P.empty("deckEdgeWood", (0, 0, 0))
    _adopt(steel, [o for o, _, _ in found])
    for o, lo, hi in found:
        dx, dy = hi.x - lo.x, hi.y - lo.y
        before = set(bpy.data.objects.keys())
        tag = o.name
        rename = lambda n, tag=tag: f"{n}_{tag}"
        if o.name in side_names:
            left = (lo.x + hi.x) / 2 > 0
            PL.call(part_wood_edge, round(dy, 3), round(hi.z - lo.z, 3), round(dx, 3),
                    at=PL.Place.at(hi.x if left else lo.x, (lo.y + hi.y) / 2, lo.z, mirror_x=not left), rename=rename)
        else:
            full = x_max is not None and abs(hi.x - x_max) < 0.01 and abs(lo.x + x_max) < 0.01
            length = dx - 2 * side_t if full else dx
            front = (lo.y + hi.y) / 2 < y_mid
            PL.call(part_wood_edge, round(length, 3), round(hi.z - lo.z, 3), round(dy, 3),
                    at=PL.Place.at((lo.x + hi.x) / 2, lo.y if front else hi.y, lo.z, rot_z=math.radians(-90 if front else 90)),
                    rename=rename)
        _adopt(wood, [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before])
    bpy.context.view_layer.update()
