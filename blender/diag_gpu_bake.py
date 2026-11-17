"""Diagnostika: proč je GPU (OptiX) pečení pomalejší než CPU - měří čas zvlášť pro nastavení zařízení,
první a druhé pečení (odliší jednorázovou režii od trvalé rychlosti za běh) - Pavel 2026-10-07.

blender.exe -b --python blender\\diag_gpu_bake.py -- gpu|cpu
"""
import sys
import time

import bpy

t_start = time.time()


def mark(label):
    print(f"T+{time.time() - t_start:7.2f}s  {label}", flush=True)


mode = (sys.argv[sys.argv.index("--") + 1:] or ["cpu"])[0]
mark(f"start, mode={mode}")

bpy.ops.wm.read_factory_settings(use_empty=True)
mark("factory settings")

sc = bpy.context.scene
sc.render.engine = "CYCLES"
if mode == "gpu":
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == "OPTIX"
    sc.cycles.device = "GPU"
    mark(f"GPU device set ({[d.name for d in prefs.devices if d.use]})")
else:
    sc.cycles.device = "CPU"
    mark("CPU device set")

sc.cycles.samples = 8
sc.render.bake.margin = 6

# jednoduchá rovina s materiálem a UV, jako při skutečném pečení vmask
bpy.ops.mesh.primitive_plane_add(size=2)
obj = bpy.context.active_object
mat = bpy.data.materials.new("diag_mat")
mat.use_nodes = True
obj.data.materials.append(mat)
img = bpy.data.images.new("diag_bake", 512, 512, alpha=True)
nt = mat.node_tree
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = img
nt.nodes.active = tex
mark("scéna připravena (1 rovina, 512x512 cíl)")

for i in range(3):
    t0 = time.time()
    bpy.ops.object.bake(type="EMIT", margin=6)
    mark(f"bake #{i + 1} hotový (trvalo {time.time() - t0:.2f}s)")

mark("konec")
