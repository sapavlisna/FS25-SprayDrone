"""Prach při práci mlýnku: částicový efekt do mod/.../effects/millDust.i3d.

    python blender/build_mill_dust.py          (Blender není potřeba)

Stejná technika jako mlha postřiku (build_spray_mist.py): ručně psané i3d s Dynamics, emitor z i3dConverteru, kouřový atlas
smoke6x6 na psSubUVShader. Dva systémy:
  millDust0 (vstup): lehký prach u výsypky šneku do mlýna; emitor míří dolů (normála -Y), skript ho otočí nahoru
  millDust1 (výstup): jemný prach z ústí foukací roury do big bagu, letí dolů a rozpíná se

Částice: rychlost v m/ms, do stran tangentSpeed (poměr k rychlosti po normále), životnost v ms.
"""

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_spray_mist as mist  # noqa: E402

OUT_DIR = mist.OUT_DIR
NAME = "millDust"

# název, hustota (částic/ms), životnost (ms), rychlost (m/ms), poměr bočního pohybu, tlumení, velikost sprite (m) na začátku a konci, krytí, strop částic
SYSTEMS = (
    ("millDustIn", dict(rate=0.010, lifespan=1800, speed=0.00035, tangent=1.0, damping=0.0, size=(0.12, 0.55), blend=0.22, max_count=120)),
    ("millDustOut", dict(rate=0.014, lifespan=2200, speed=0.00050, tangent=1.2, damping=0.0, size=(0.20, 0.90), blend=0.20, max_count=200)),
)


def particle_system(dyn_id, name, rate, lifespan, speed, tangent, damping, size, blend, max_count):
    gain = (size[1] - size[0]) / lifespan
    return (f'    <ParticleSystem name="{name}" dynamicId="{dyn_id}" type="sprite" rate="{rate}" lifespan="{lifespan}" '
            f'maxCount="{max_count}" speed="{speed:.6f}" speedRandom="{speed * 0.25:.6f}" tangentSpeed="{tangent:.3f}" '
            f'normalSpeed="1" damping="{damping}" spriteScaleX="{size[0]}" spriteScaleY="{size[0]}" '
            f'spriteScaleXGain="{gain:.6f}" spriteScaleYGain="{gain:.6f}" blendFactor="{blend}" blendInFactor="0.25" '
            f'blendOutFactor="0.7" depthSort="true" randomInitRotation="true" deltaRotateMin="-0.0003" '
            f'deltaRotateMax="0.0003" textureAtlasSizeX="6" textureAtlasSizeY="6">\n'
            f'      <Gravity force="0 0 0"/>\n'
            f'    </ParticleSystem>')


def write_i3d(path):
    systems = "\n".join(particle_system(i + 1, n, **kw) for i, (n, kw) in enumerate(SYSTEMS))
    nodes = []
    for i, (n, _) in enumerate(SYSTEMS):
        base = 10 + i * 2
        nodes.append(f'    <Dynamic name="{n}" dynamicId="{i + 1}" emitterShapeNodeId="{base + 1}" clipDistance="80" '
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
    <Material name="dust_mat" materialId="6" alphaBlending="true" customShaderId="4" customShaderVariation="subUV" shadingRate="4x4">
      <Texture fileId="1"/>
      <Normalmap fileId="2"/>
      <Glossmap fileId="3"/>
      <CustomParameter name="playScale" value="20 40 1 0"/>
      <CustomParameter name="colorAlpha" value="0.94 0.94 0.92 1"/>
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
    tmp = mist.export_shapes()
    os.makedirs(OUT_DIR, exist_ok=True)
    shutil.copyfile(tmp + ".shapes", os.path.join(OUT_DIR, f"{NAME}.i3d.shapes"))
    write_i3d(os.path.join(OUT_DIR, f"{NAME}.i3d"))
    print("millDust:", os.path.join(OUT_DIR, f"{NAME}.i3d"))


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
