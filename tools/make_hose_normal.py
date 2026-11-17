"""Normálová textura spirálově vyztužené hadice: jedna šroubovice na dlaždici (v UV od rohu k rohu), plynule navazující ve směru U (po obvodu)
i V (po délce). Hadice je válec s UV obvod 0..1 a délka 0..N; N dlaždic na délku = N závitů.

python tools/make_hose_normal.py [vystup.dds]   výchozí mod/FS25_SprayDroneTrailer/textures/sdt_hose_normal.dds

Alfa = x složky (kdyby shader četl normálu jako DXT5nm), RGB = tangentní normála.
"""

import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE = 128
STRENGTH = 2.4


def build():
    u = (np.arange(SIZE) + 0.5) / SIZE
    uu, vv = np.meshgrid(u, u)
    phase = (vv - uu) % 1.0
    h = 0.5 - 0.5 * np.cos(2 * math.pi * phase)
    h = np.clip(h * 1.35 - 0.15, 0.0, 1.0)
    dh = np.gradient(np.pad(h, 1, mode="wrap"), axis=(0, 1))
    dv = dh[0][1:-1, 1:-1] * SIZE
    du = dh[1][1:-1, 1:-1] * SIZE
    nx, ny = -du * STRENGTH / SIZE * 4, -dv * STRENGTH / SIZE * 4
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    rgb = np.stack([nx, ny, nz], axis=-1) * 0.5 + 0.5
    img = np.concatenate([rgb, rgb[..., :1]], axis=-1)
    return Image.fromarray((img * 255).round().astype(np.uint8), "RGBA")


def main():
    dst = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "mod", "FS25_SprayDroneTrailer", "textures", "sdt_hose_normal.dds")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    png = os.path.join(ROOT, "tmp", "p1", "sdt_hose_normal.png")
    build().save(png)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "png2dds.py"), png, dst, "--format", "rgba", "--linear"], check=True)
    print(dst)


if __name__ == "__main__":
    main()
