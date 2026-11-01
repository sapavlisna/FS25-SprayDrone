"""Sdílené rozměry mezi moduly, které staví hlavní nádrž (sdt_bigtank.py) a rozvod / mixér (sdt_tanks.py).

Všechny velikosti hlavní nádrže (800 / 1000 / 1500 l válcové, 3000 / 5000 l hranaté) mají výpust na stejném místě, takže
rozvod k čerpadlu je pro všechny stejný. Souřadnice v Blenderu (kořen vleku, m): +X vlevo, -Y dopředu (k oji), Z nahoru.
"""

from mathutils import Vector

from decal_layout import TANK_SIZES  # noqa: F401
MAIN_TANK_Y_FRONT = -0.30                 # přední konec všech nádrží (zadní konec se s velikostí posouvá dozadu)
MAIN_DRAIN = Vector((0.125, -0.239, 1.0025))   # konec výpustného nátrubku (dole vpředu, vpravo od středu)
MAIN_DRAIN_DIR = Vector((0.0, -1.0, 0.0))      # nátrubek míří dopředu (-Y)
