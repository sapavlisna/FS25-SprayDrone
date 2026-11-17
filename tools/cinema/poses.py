"""Vypíše polohu a směr jízdy souprav (pickup, vlek, ...) z běžící hry: python tools/cinema/poses.py [alias ...]"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cinema_client import ev  # noqa: E402

CODE = """
local out = {}
for _, alias in ipairs({%s}) do
    local v = SprayDroneCinema.findVehicle(alias)
    if v ~= nil then
        local x, y, z = getWorldTranslation(v.rootNode)
        local dx, dy, dz = localDirectionToWorld(v.rootNode, 0, 0, 1)
        table.insert(out, string.format("%%s pos %%.1f %%.1f %%.1f yaw %%.0f pitch %%.1f v=%%.1f", alias, x, y, z, math.deg(math.atan2(dx, dz)) %% 360, math.deg(math.asin(dy)), v:getLastSpeed()))
    end
end
return table.concat(out, " | ")
"""

aliases = sys.argv[1:] or ["pickup", "middle"]
print(ev(CODE % ", ".join('"%s"' % a for a in aliases))[1])
