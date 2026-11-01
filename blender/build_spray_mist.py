"""Mlha z trysek dronu: částicový efekt (kužel od trysky k zemi) do mod/.../effects/sprayMist.i3d.

    python blender/build_spray_mist.py          (Blender není potřeba)

Exportér GIANTS částicové systémy nezná, proto se i3d s nastavením částic (Dynamics) píše ručně. .shapes s emitorem
vyrobí oficiální i3dConverter z exportéru (stejný, který volá Blender): emitor je malý čtyřúhelník
(4 vrcholy, 2 trojúhelníky, normála a UV) jako ve vanilla efektech (sprayCan, soilParticle) a musí mít `meshUsage` 260
(CPU mesh 256 + příznak emitoru 4), tedy volby 0x01040003 v hlavičce tvaru. Bez příznaku emitoru a bez UV hra při prvním
spuštění částic hlásila "Particle System emitter mesh ... could not be loaded". Tři varianty (S, M, L) se liší
rozevřením kužele podle záběru a polohy trysek, viz VARIANTS.

Částice: rychlost v m/ms, dolů rychlostí h / životnost, do stran tangentSpeed = poloměr u země / h (náhodně 0..max).
"""

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
OUT_DIR = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer", "effects")
TMP_DIR = os.path.join(PROJECT, "out", "spray")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdt_paths  # noqa: E402

GAME_DIR = sdt_paths.GAME_DIR
CONVERTER = os.path.join(PROJECT, "tools", "io_export_i3d_reworked_10.0.16_oficialni_konvertor",
                         "io_export_i3d_reworked", "util", "i3dConverter.exe")
NAME = "sprayMist"

LIFESPAN = 1100          # ms
SPRAY_HEIGHT = 3.4       # m od trysky k zemi při sprayHeight 3 m (trysky jsou ~0,4 m nad kořenem dronu)
EMITTER_HALF = 0.03      # m, polovina strany čtyřúhelníku emitoru
MESH_USAGE_EMITTER = 256 | 4
# poloměr kužele u země (m), hustota (částic/ms), počáteční a koncová velikost sprite (m), krytí sprite, strop částic
VARIANTS = (
    ("mistS", dict(radius=2.3, rate=0.056, size=(0.15, 1.0), blend=0.45, max_count=800)),
    ("mistM", dict(radius=3.4, rate=0.056, size=(0.15, 1.1), blend=0.45, max_count=800)),
    ("mistL", dict(radius=4.5, rate=0.068, size=(0.20, 1.4), blend=0.45, max_count=1000)),
)


def export_shapes():
    """Vrátí cestu k .shapes s emitorem. Čtyřúhelník leží v rovině XZ a normála míří dolů (-Y), částice letí po normále."""
    h = EMITTER_HALF
    verts = ((-h, h, 0, 0), (h, h, 1, 0), (-h, -h, 0, 1), (h, -h, 1, 1))
    vx = chr(10).join(f'        <v p="{x} 0 {z}" n="0 -1 0" t0="{u} {v}"/>' for x, z, u, v in verts)
    xml = f'''<?xml version="1.0" encoding="iso-8859-1"?>
<i3D name="mist_tmp" version="1.6">
  <Asset><Export program="i3dConverter" version="1.0"/></Asset>
  <Files/>
  <Materials>
    <Material name="lambert1" materialId="1" diffuseColor="0.494118 0.494118 0.494118 1"/>
  </Materials>
  <Shapes>
    <IndexedTriangleSet name="mistEmitShape" shapeId="1" meshUsage="{MESH_USAGE_EMITTER}">
      <Vertices count="4" normal="true" uv0="true">
{vx}
      </Vertices>
      <Triangles count="2">
        <t vi="0 2 1"/>
        <t vi="2 3 1"/>
      </Triangles>
      <Subsets count="1">
        <Subset firstVertex="0" numVertices="4" firstIndex="0" numIndices="6" uvDensity0="1"/>
      </Subsets>
    </IndexedTriangleSet>
  </Shapes>
  <Scene>
    <Shape name="mistEmitShape" shapeId="1" nodeId="4" nonRenderable="true" materialIds="1"/>
  </Scene>
</i3D>
'''
    os.makedirs(TMP_DIR, exist_ok=True)
    tmp = os.path.join(TMP_DIR, "mist_tmp.i3d")
    for f in (tmp, tmp + ".shapes"):
        if os.path.exists(f):
            os.remove(f)
    with open(tmp, "w", encoding="iso-8859-1", newline="\n") as f:
        f.write(xml)
    result = subprocess.run([CONVERTER, "-in", tmp, "-out", tmp, "-gamePath", GAME_DIR], capture_output=True, text=True)
    if not os.path.exists(tmp + ".shapes"):
        raise RuntimeError("i3dConverter nevytvořil .shapes: " + result.stdout[-500:] + result.stderr[-500:])
    return tmp


def particle_system(dyn_id, name, radius, rate, size, speed_scale=1.0, normal=1, damping=0, blend=0.16, max_count=600):
    speed = SPRAY_HEIGHT / LIFESPAN * speed_scale
    tangent = radius / SPRAY_HEIGHT
    gain = (size[1] - size[0]) / LIFESPAN
    return (f'    <ParticleSystem name="{name}" dynamicId="{dyn_id}" type="sprite" rate="{rate}" lifespan="{LIFESPAN}" '
            f'maxCount="{max_count}" speed="{speed:.6f}" speedRandom="{speed * 0.12:.6f}" tangentSpeed="{tangent:.3f}" '
            f'normalSpeed="{normal}" damping="{damping}" spriteScaleX="{size[0]}" spriteScaleY="{size[0]}" '
            f'spriteScaleXGain="{gain:.6f}" spriteScaleYGain="{gain:.6f}" blendFactor="{blend}" blendInFactor="0.2" '
            f'blendOutFactor="0.7" depthSort="true" randomInitRotation="true" deltaRotateMin="-0.0004" '
            f'deltaRotateMax="0.0004" textureAtlasSizeX="6" textureAtlasSizeY="6">\n'
            f'      <Gravity force="0 0 0"/>\n'
            f'    </ParticleSystem>')


def write_i3d(path):
    systems = "\n".join(particle_system(i + 1, n, **kw) for i, (n, kw) in enumerate(VARIANTS))
    nodes = []
    for i, (n, _) in enumerate(VARIANTS):
        base = 10 + i * 2
        nodes.append(f'    <Dynamic name="{n}" dynamicId="{i + 1}" emitterShapeNodeId="{base + 1}" clipDistance="120" '
                     f'nodeId="{base}" castsShadows="false" receiveShadows="false" distanceBlending="false" '
                     f'materialIds="6">\n'
                     f'      <Shape name="mistEmitShape" shapeId="1" nodeId="{base + 1}" castsShadows="false" '
                     f'receiveShadows="false" nonRenderable="true" materialIds="5"/>\n'
                     f'    </Dynamic>')
    xml = f'''<?xml version="1.0" encoding="iso-8859-1"?>

<i3D name="{NAME}" version="1.6" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://i3d.giants.ch/schema/i3d-1.6.xsd">
  <Files>
    <File fileId="1" filename="$data/effects/smoke/smoke6x6_diffuse.png"/>
    <File fileId="2" filename="$data/effects/smoke/smoke6x6_normal.png"/>
    <File fileId="4" filename="$data/shaders/psSubUVShader.xml"/>
    <File fileId="3" filename="$data/shared/default_specular.png"/>
  </Files>

  <Materials>
    <Material name="lambert1" materialId="5" diffuseColor="0.494118 0.494118 0.494118 1">
    </Material>
    <Material name="mist_mat" materialId="6" alphaBlending="true" customShaderId="4" customShaderVariation="subUV" shadingRate="4x4">
      <Texture fileId="1"/>
      <Normalmap fileId="2"/>
      <Glossmap fileId="3"/>
      <CustomParameter name="playScale" value="20 40 1 0"/>
      <CustomParameter name="colorAlpha" value="1 1 1 1"/>
    </Material>
  </Materials>

  <Shapes externalShapesFile="{NAME}.i3d.shapes">
  </Shapes>

  <Dynamics>
{systems}
  </Dynamics>

  <Scene>
    <TransformGroup name="{NAME}" nodeId="1">
{chr(10).join(nodes)}
    </TransformGroup>
  </Scene>
</i3D>
'''
    with open(path, "w", encoding="iso-8859-1", newline="\n") as f:
        f.write(xml)


def main():
    tmp = export_shapes()
    os.makedirs(OUT_DIR, exist_ok=True)
    shutil.copyfile(tmp + ".shapes", os.path.join(OUT_DIR, f"{NAME}.i3d.shapes"))
    write_i3d(os.path.join(OUT_DIR, f"{NAME}.i3d"))
    print("sprayMist:", os.path.join(OUT_DIR, f"{NAME}.i3d"))


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
