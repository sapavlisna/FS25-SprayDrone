"""Polepky na dílech vleku, které staví sdt_tanks.py a sdt_mixer.py: štítek a stupnice koncentrátové nádrže, výrobní
štítek a šipky toku na mixéru, popisky na rolovacích vratech skříně na kanystry (Toolbox_DoorPanel).

Polohy se odvozují z týchž konstant jako geometrie dílů. Polepky na kanystrech nejsou (kanystry se přebarvují).
"""

import bpy
from mathutils import Matrix, Vector

import decal_layout as L
import sdt_mixer as X
import sdt_parts as P
import sdt_tanks as T
from sdt_bigtank import decal_sub_uv

# stupnice koncentrátové nádrže: výška rysek nad zemí (l -> m), viz sdt_tanks._induction_scale; čísla leží na +Y straně pruhu
CONC_TICK_Z = {10: 1.177, 20: 1.246, 30: 1.314, 40: 1.383, 50: 1.451}
CONC_NUM_Y = 0.075                    # střed čísel od osy nádrže na +Y (rysky končí 0,019..0,038 od osy)
CONC_NUM_SIZE = (0.05, 0.03)


def _concentrate(z):
    ix, iy = T.INDUCTION_XY
    R = T.INDUCTION_R
    zj = z + T.INDUCTION_STAND_H + T.INDUCTION_CONE_H
    hw = 0.065
    face = iy - R - 0.003                                          # čelní plocha bílé podložky pro štítek
    m = 0.003
    P.decal_quad("Decal_ConcLabel", (ix - hw + m, face, zj + 0.115 + m), (1, 0, 0), (0, 0, 1), 2 * hw - 2 * m,
                 0.100 - 2 * m, "concLabel")
    shell = bpy.data.objects["Tank_Induction"]
    x = ix - R
    for k, (litres, zt) in enumerate(CONC_TICK_Z.items()):
        d = P.conform_decal(f"Decal_ConcNum{litres}", shell, Vector((x, iy + CONC_NUM_Y, zt)), Vector((-1, 0, 0)),
                            Vector((0, 0, 1)), CONC_NUM_SIZE[0], CONC_NUM_SIZE[1], "concNums", offset=0.0022, cols=4,
                            rows=4)
        decal_sub_uv(d, "concNums", L.CONC_NUMS_SUB[k])


def _mixer(z):
    c = T.pump_ports(*T.PUMP_XY, z)["tee"]
    face = c.y - X.CH_Y - 0.0025                                   # čelo hliníkového štítku na přední stěně komory
    P.decal_quad("Decal_MixPlate", (c.x - 0.052, face, c.z - 0.058), (1, 0, 0), (0, 0, 1), 0.104, 0.028, "mixPlate")
    wall = c.y - X.CH_Y
    for k, sx in enumerate((1, -1)):                               # voda přichází zprava (+X), koncentrát zleva
        x0 = c.x + sx * 0.043 if sx > 0 else c.x - 0.073
        P.decal_quad(f"Decal_MixArrow{k}", (x0, wall, c.z + 0.010), (1, 0, 0), (0, 0, 1), 0.030, 0.0135, "mixArrow",
                         L.MIX_ARROW_SUB[k])


def _toolbox_lid(z):
    """Popisky na vratech skříně na kanystry (Toolbox_DoorPanel, dítě pivotu Toolbox_Door - viz
    build_trailer_middle.build_cabinet_door), čelem ven z vleku (+Y), po celé šířce a výšce vrat (Pavel 2026-10-11: větší
    a víc nálepek, čitelné z odstupu): výstražné pruhy nahoře a dole, nápis vleku, velký KANYSTRY a SERVIS / NÁŘADÍ uprostřed,
    po stranách výstražný trojúhelník, piktogramy a štítky kanystru. Jedou s vraty (jsou děti pivotu)."""
    pivot = bpy.data.objects.get("Toolbox_Door")
    panel = bpy.data.objects.get("Toolbox_DoorPanel")
    if pivot is None or panel is None:
        return
    pts = [panel.matrix_world @ Vector(c) for c in panel.bound_box]
    px0, px1 = min(p.x for p in pts), max(p.x for p in pts)
    pz0, pz1 = min(p.z for p in pts), max(p.z for p in pts)
    cx = (px0 + px1) / 2
    face = pivot.matrix_world.translation.y + 0.010 + 0.004 + 0.002      # čelo lamel (pivot je ve středu plechu t=0,02, plech o lamelu 4 mm zpět)

    def flat(name, xc, zb, w, h, region, sub=None):
        obj = P.decal_quad(name, (xc + w / 2, face, zb), (-1, 0, 0), (0, 0, 1), w, h, region, sub)
        world = obj.matrix_world.copy()
        obj.parent = pivot
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_world = world
        return obj

    full = min(1.60, px1 - px0 - 0.10)
    stripe_h = full / 16.0
    flat("Decal_LidStripeBottom", cx, pz0 + 0.04, full, stripe_h, "stripe")
    flat("Decal_LidStripeTop", cx, pz1 - 0.04 - stripe_h, full, stripe_h, "stripe")
    banner_w = 1.50
    banner_h = banner_w * 64 / 768
    conc_w, conc_h = 1.30, 1.30 * 52 / 256
    text_w, text_h = 1.30, 1.30 * 42 / 256
    z_lo, z_hi = pz0 + 0.04 + stripe_h, pz1 - 0.04 - stripe_h
    free = (z_hi - z_lo) - (text_h + conc_h + banner_h)
    gap = free / 4
    z = z_lo + gap
    flat("Decal_LidText", cx, z, text_w, text_h, "boxText")
    z += text_h + gap
    flat("Decal_LidConc", cx, z, conc_w, conc_h, "boxConc")
    z += conc_h + gap
    flat("Decal_LidBanner", cx, z, banner_w, banner_h, "sideText", (0.0, 0.0, 0.75, 1.0))
    zm = z_lo + (z_hi - z_lo) * 0.5
    side = 0.79                                                 # střed postranního sloupce od středu vrat (vedle bloku 1,30 m)
    for k, sx in enumerate((1, -1)):
        xc = cx + sx * side
        if sx > 0:
            flat("Decal_LidWarn", xc, zm + 0.04, 0.24, 0.24, "boxWarn")
            flat("Decal_LidIcon0", xc, zm - 0.24, 0.18, 0.18, "tankWarn", L.TANK_WARN_SUB[2])
        else:
            flat("Decal_LidIcon1", xc, zm + 0.04, 0.18, 0.18, "tankWarn", L.TANK_WARN_SUB[3])
            flat("Decal_LidLabel", xc, zm - 0.16, 0.24, 0.09, "canisterLabel")


def build_equipment_decals(z):
    """Volá se po sestavení výbavy (build_equipment), z = horní plocha paluby."""
    bpy.context.view_layer.update()
    _concentrate(z)
    _mixer(z)
    _toolbox_lid(z)
