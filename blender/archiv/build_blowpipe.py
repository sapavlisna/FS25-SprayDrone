"""Foukací roura mlýnku na vápno: objects/limeBigBag/blowPipe.i3d. Přídavný model (mlýnek se kvůli ní znovu neexportuje): hra ho za běhu
připojí na uzel výstupní spojky mlýnku (millOutletPort) a ukáže ho jen v režimu výstupu "big bag" (scripts/SprayDroneMill.lua).
Samostatný skript nad prázdnou scénou (postup build_limebag.py):

    blender.exe -b --python blender\\build_blowpipe.py

Počátek je čelo výstupní spojky Storz mlýnku, roura vede ven po -X (jako výstup hadice), stoupá oblým kolenem a ohnutá nad stojící vanilla big bag
($data/objects/bigBag, 1,0 x 0,84 m, s poutky do 1,74 m nad zemí) končí přírubou a rozšiřujícím se difuzorem s gumovou manžetou dolů, ústí 2,0 m nad zemí.
Uzel blowNozzle je střed ústí difuzoru; jeho poloha vůči počátku (x, výška, z v souřadnicích i3d)
je NOZZLE a musí sedět s <bagOutput nozzle=...> v sdtLimeMill.xml. Materiály jako u pumpy a mlýnku (vehicleShader z knihovny hry).
"""

import math
import os
import sys

import addon_utils
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_canister as C  # noqa: E402
import build_limebag as B  # noqa: E402
import build_link_items as L  # noqa: E402
import export_middle_mod as X  # noqa: E402
import sdt_parts as P  # noqa: E402
from sdt_tanks import Mesh, V  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT_DIR = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer", "objects", "limeBigBag")
WORK = os.path.join(PROJECT, "out", "limebigbag")
NAME = "blowPipe"

R = 0.062                 # poloměr roury
BEND = 0.17               # poloměr ohybu osy
RISE_X = -0.42            # svislý úsek roury, vzdálenost od čela spojky
TOP_Z = 1.72              # výška vodorovného úseku nad osou spojky
END_X = -1.55             # osa hubice vůči spojce
NOZZLE_Z = 1.30           # ústí difuzoru nad osou spojky (osa spojky je 0,70 m nad zemí => ústí 2,0 m nad zemí, nad poutky big bagu 1,74 m)
DIFFUSER_L = 0.16         # délka difuzoru, nad ní příruba na konci roury
RD = 0.165                # poloměr ústí difuzoru
PATH = [V(0.0, 0.0, 0.0), V(RISE_X, 0.0, 0.0), V(RISE_X, 0.0, TOP_Z), V(END_X, 0.0, TOP_Z), V(END_X, 0.0, NOZZLE_Z + DIFFUSER_L + 0.04)]
NOZZLE = (END_X, NOZZLE_Z, 0.0)   # v souřadnicích i3d (x, výška, z): z Blenderu (x, y, z) -> (x, z, -y)


def rounded_path(points, radius, step=0.035):
    """Lomená čára se zaoblenými rohy: vrací hustě vzorkované body osy."""
    out = [points[0]]
    for i in range(1, len(points) - 1):
        a, b, c = points[i - 1], points[i], points[i + 1]
        d0, d1 = (a - b).normalized(), (c - b).normalized()
        angle = d0.angle(d1)
        t = min(radius / math.tan(angle / 2), (a - b).length * 0.45, (c - b).length * 0.45)
        r = t * math.tan(angle / 2)
        p0, p1 = b + d0 * t, b + d1 * t
        centre = b + (d0 + d1).normalized() * (r / math.sin(angle / 2))
        v0, v1 = (p0 - centre), (p1 - centre)
        sweep = v0.angle(v1)
        n = max(3, int(r * sweep / step))
        axis = v0.cross(v1).normalized()
        for k in range(n + 1):
            out.append(centre + Matrix.Rotation(sweep * k / n, 3, axis) @ v0)
    out.append(points[-1])
    return out


def tube(m, pts, r, mat):
    for a, b in zip(pts, pts[1:]):
        m.cyl(a, b, r, mat, seg=14, caps=False)
    for p in pts[1:-1]:
        m.sphere(p, r, mat, seg=14, rings=6)


def flange_joint(m, p, axis, r_out=0.098, bolts=8):
    """Přírubový spoj dílů roury v bodě p na ose roury (směr axis): dvě příruby s gumovým těsněním mezi nimi, na obvodu šrouby s maticemi."""
    axis = Vector(axis).normalized()
    m.cyl(p - axis * 0.011, p - axis * 0.001, r_out, "SDT_Alu", seg=28)
    m.cyl(p - axis * 0.001, p + axis * 0.003, r_out - 0.004, "SDT_Rubber", seg=28)
    m.cyl(p + axis * 0.003, p + axis * 0.013, r_out, "SDT_Alu", seg=28)
    m.bolt_circle(p - axis * 0.011, -axis, r_out - 0.016, bolts, 0.0075, 0.007, "SDT_Steel", phase=math.pi / bolts)
    m.bolt_circle(p + axis * 0.013, axis, r_out - 0.016, bolts, 0.0085, 0.008, "SDT_Steel", phase=math.pi / bolts)


def build_mesh(name):
    m = Mesh(name)
    pts = rounded_path(PATH, BEND)
    tube(m, pts, R, "SDT_Steel")
    # spojka Storz na ústí mlýnku: hliníková příruba, červený zajišťovací kroužek, drápy
    m.cyl(V(0.0, 0.0, 0.0), V(-0.05, 0.0, 0.0), 0.095, "SDT_Alu", seg=24)
    m.cyl(V(-0.05, 0.0, 0.0), V(-0.085, 0.0, 0.0), 0.088, "SDT_PaintRed", seg=24)
    m.torus(V(-0.085, 0.0, 0.0), V(1, 0, 0), 0.075, 0.006, "SDT_Steel", seg=24, rseg=5)
    for k in range(3):
        a = 2 * math.pi * k / 3 + math.pi / 2
        m.obox((0.03, 0.028, 0.03), Matrix.Translation(V(-0.025, 0.1 * math.cos(a), 0.1 * math.sin(a))), "SDT_Alu", bevel=0.004)
    # příruby se šrouby a gumovým těsněním na spojích dílů roury: ve svislém a vodorovném úseku a před difuzorem
    flange_joint(m, V(RISE_X, 0.0, 0.78), V(0, 0, 1))
    flange_joint(m, V(-1.00, 0.0, TOP_Z), V(-1, 0, 0))
    flange_joint(m, V(END_X, 0.0, NOZZLE_Z + DIFFUSER_L + 0.04), V(0, 0, -1))
    # pásové spony na svislém a vodorovném úseku
    for z in (0.30, 1.12):
        m.torus(V(RISE_X, 0.0, z), V(0, 0, 1), R + 0.006, 0.007, "SDT_Alu", seg=24, rseg=5)
    for x in (-0.66, -1.34):
        m.torus(V(x, 0.0, TOP_Z), V(1, 0, 0), R + 0.006, 0.007, "SDT_Alu", seg=24, rseg=5)
    # vzpěry: z konzoly na svislém úseku k vodorovnému úseku a k patě svislého úseku
    m.cyl(V(RISE_X, 0.0, 1.10), V(-0.85, 0.0, TOP_Z - 0.05), 0.016, "SDT_Frame", seg=10)
    m.cyl(V(RISE_X, 0.0, 0.55), V(0.0, 0.0, 0.20), 0.016, "SDT_Frame", seg=10)
    # difuzor: kuželový nástavec z roury na ústí Ø 0,33 m s lemem, gumová manžeta proti prachu a žlutý pásek
    nz = V(END_X, 0.0, NOZZLE_Z)
    top = nz + V(0, 0, DIFFUSER_L)
    m.cyl(top, nz + V(0, 0, 0.060), R + 0.004, "SDT_Steel", r1=RD - 0.012, seg=32, caps=False)
    m.cyl(nz + V(0, 0, 0.060), nz + V(0, 0, 0.012), RD - 0.012, "SDT_Steel", seg=32, caps=False)
    m.torus(nz + V(0, 0, 0.012), V(0, 0, 1), RD - 0.006, 0.008, "SDT_Steel", seg=32, rseg=5)
    m.cyl(nz + V(0, 0, 0.012), nz + V(0, 0, -0.050), RD, "SDT_Rubber", r1=RD + 0.014, seg=32, caps=False)
    m.torus(nz + V(0, 0, -0.050), V(0, 0, 1), RD + 0.014, 0.007, "SDT_Rubber", seg=32, rseg=5)
    m.torus(nz + V(0, 0, 0.004), V(0, 0, 1), RD + 0.004, 0.006, "SDT_PaintYellow", seg=32, rseg=5)
    for k in range(3):
        a = 2 * math.pi * k / 3
        m.cyl(top + V(0.058 * math.cos(a), 0.058 * math.sin(a), 0.0), nz + V(0.150 * math.cos(a), 0.150 * math.sin(a), 0.026), 0.004,
              "SDT_Steel", seg=6)
    return m.finish()


def build():
    C.wipe()
    P._coll = bpy.context.scene.collection
    root = bpy.data.objects.new(NAME, None)
    bpy.context.scene.collection.objects.link(root)
    P._root = root
    vis = build_mesh(f"{NAME}_vis")
    C.props(vis, clipDistance=60.0)
    L._pivot("blowNozzle", (END_X, 0.0, NOZZLE_Z), root)
    bpy.context.view_layer.update()
    return root, vis


def export(root):
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{NAME}.i3d")
    C.export_i3d(root, path)
    L.shader_materials(path)
    C.zero_density(path)
    names = [root.name, f"{NAME}_vis", "blowNozzle"]
    mappings, found = X.i3d_mappings(path, names)
    print(mappings)


def preview(root):
    """Náhledy: pod difuzorem stojí vanilla big bag (vak 1,0 x 0,84 x 1,37 m s poutky do 1,74 m), vedle výstupu mlýnku boční stěna a podlaha (jen pro snímky, mimo export)."""
    def mesh_box(name, x0, x1, y0, y1, z0, z1, color):
        me = bpy.data.meshes.new(name)
        verts = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
        me.from_pydata(verts, [], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
        me.update()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        mat = B.flat_material(name, color)
        ob.data.materials.append(mat)
        return ob
    mesh_box("pv_ground", -4.0, 2.0, -2.5, 2.5, -0.74, -0.70, (0.45, 0.43, 0.40, 1))
    mesh_box("pv_bag", END_X - 0.495, END_X + 0.495, -0.42, 0.42, -0.70, 0.67, (0.85, 0.85, 0.80, 1))
    for sx in (-1, 1):
        mesh_box(f"pv_loop{sx}", END_X + sx * 0.17 - 0.07, END_X + sx * 0.17 + 0.07, -0.015, 0.015, 0.50, 1.035, (0.80, 0.80, 0.72, 1))
    mesh_box("pv_mill", -0.06, 1.4, -1.2, 1.2, -0.70, 1.9, (0.30, 0.32, 0.36, 1))
    bpy.context.view_layer.update()
    for name, direction in (("iso", Vector((0.35, -0.9, 0.35))), ("side", Vector((0.0, -1.0, 0.1))), ("front", Vector((-1.0, 0.0, 0.1)))):
        B.render(os.path.join(WORK, f"prev_{name}.png"), direction, size=(1200, 900))


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("io_export_i3d_reworked", default_set=False)
    root, vis = build()
    export(root)
    preview(root)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
