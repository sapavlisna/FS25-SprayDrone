"""PNG -> DDS s mipmapami přes Pillow (BC1/DXT1 bez alfy, BC3/DXT5 s alfou, nebo nekomprimované A8R8G8B8).

python tools/png2dds.py vstup.png vystup.dds [--format dxt1|dxt5|rgba] [--no-mips] [--linear] [--size N] [--matte R,G,B]

Pillow umí zapsat BCn jen jako jednu úroveň, mipmapy se proto skládají po úrovních pod vlastní hlavičku.
--linear zmenšuje mipmapy v lineárním prostoru bez převodu z sRGB (masky, vmask).
"""

import argparse
import io
import struct

from PIL import Image

DDSD_CAPS, DDSD_HEIGHT, DDSD_WIDTH, DDSD_PITCH = 0x1, 0x2, 0x4, 0x8
DDSD_PIXELFORMAT, DDSD_MIPMAPCOUNT, DDSD_LINEARSIZE = 0x1000, 0x20000, 0x80000
DDSCAPS_COMPLEX, DDSCAPS_TEXTURE, DDSCAPS_MIPMAP = 0x8, 0x1000, 0x400000


def _levels(img, mips, linear):
    """Mipmapy. Textura s alfou jde krabicovým filtrem z předchozí úrovně: pixel je průhledný, právě když je průhledný celý
    jeho blok v plné velikosti (LANCZOS z plné velikosti roztahoval alfu až ~60/255 do průhledných míst - lem kolem polepů)."""
    out = [img]
    if not mips:
        return out
    w, h = img.size
    cur = img
    while w > 4 and h > 4:
        w, h = w // 2, h // 2
        if linear or img.mode == "RGBA":
            cur = cur.resize((w, h), Image.BOX)
        else:
            cur = img.resize((w, h), Image.LANCZOS)
        out.append(cur)
    return out


def _bcn(level, fmt):
    buf = io.BytesIO()
    level.save(buf, "DDS", pixel_format=fmt.upper())
    return buf.getvalue()[128:]


def convert(src, dst, fmt="dxt1", mips=True, linear=False, size=None, matte=None):
    img = Image.open(src)
    if matte is not None:
        # ikona módu je bez alfy: průhledné pozadí renderu se položí na plnou barvu
        img = img.convert("RGBA")
        img = Image.alpha_composite(Image.new("RGBA", img.size, tuple(matte) + (255,)), img)
    img = img.convert("RGBA" if fmt in ("dxt5", "rgba") else "RGB")
    if size:
        img = img.resize((size, size), Image.LANCZOS)
    w, h = img.size
    levels = _levels(img, mips, linear)
    flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT
    caps = DDSCAPS_TEXTURE
    if len(levels) > 1:
        flags |= DDSD_MIPMAPCOUNT
        caps |= DDSCAPS_COMPLEX | DDSCAPS_MIPMAP
    if fmt == "rgba":
        body = b""
        for lv in levels:
            r, g, b, a = lv.split()
            body += Image.merge("RGBA", (b, g, r, a)).tobytes()
        flags |= DDSD_PITCH
        pitch = w * 4
        pf = struct.pack("<II4sIIIII", 32, 0x41, b"\0\0\0\0", 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    else:
        body = b"".join(_bcn(lv, fmt) for lv in levels)
        flags |= DDSD_LINEARSIZE
        pitch = max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * (8 if fmt == "dxt1" else 16)
        pf = struct.pack("<II4sIIIII", 32, 0x4, fmt.upper().encode(), 0, 0, 0, 0, 0)
    header = struct.pack("<4sIIIIIII44x", b"DDS ", 124, flags, h, w, pitch, 0, len(levels)) + pf + \
        struct.pack("<IIII4x", caps, 0, 0, 0)
    with open(dst, "wb") as f:
        f.write(header + body)
    return len(levels)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--format", default="dxt1", choices=("dxt1", "dxt5", "rgba"))
    ap.add_argument("--no-mips", action="store_true")
    ap.add_argument("--linear", action="store_true")
    ap.add_argument("--size", type=int, help="zmenšit na čtverec size x size")
    ap.add_argument("--matte", help="R,G,B: položit průhledné pozadí na tuto barvu")
    a = ap.parse_args()
    matte = [int(v) for v in a.matte.split(",")] if a.matte else None
    n = convert(a.src, a.dst, a.format, not a.no_mips, a.linear, a.size, matte)
    print(f"{a.dst}: {a.format}, {n} úrovní")


if __name__ == "__main__":
    main()
